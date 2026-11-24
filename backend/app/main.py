import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, load_settings
from .db import Database
from .llm import AllProvidersUnavailable, LLMGateway, parse_failure_header
from .schemas import ChatRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


def create_app(settings: Settings = None) -> FastAPI:
    settings = settings or load_settings()
    db = Database(settings.db_path)
    gateway = LLMGateway(
        settings.api_keys,
        settings.model,
        settings.request_timeout,
        settings.max_tokens,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.init()  # schema is created on startup
        await gateway.warmup()
        yield

    app = FastAPI(title="LLM Chatbot", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error")
        return JSONResponse({"detail": "internal server error"}, status_code=500)

    @app.get("/health")
    async def health():
        db_ok = await asyncio.to_thread(db.ping)
        if not db_ok or not settings.api_keys:
            raise HTTPException(503, "not ready")
        return {
            "status": "ok",
            "keys_configured": len(settings.api_keys),
            "cache_enabled": True,
        }

    @app.post("/chat")
    async def chat(req: ChatRequest, request: Request):
        started = time.perf_counter()

        simulate = {}
        if settings.enable_failure_simulation:
            simulate = parse_failure_header(
                request.headers.get("x-simulate-failure", "")
            )

        stored_prompt = await asyncio.to_thread(
            db.get_system_prompt, req.session_id
        )
        history = await asyncio.to_thread(db.get_history, req.session_id)
        system_prompt = (
            req.system_prompt or stored_prompt or settings.default_system_prompt
        )
        messages = (
            [{"role": "system", "content": system_prompt}]
            + history
            + [{"role": "user", "content": req.message}]
        )

        try:
            result = await gateway.complete(messages, simulate)
        except AllProvidersUnavailable:
            # Nothing is saved on failure.
            raise HTTPException(503, "all providers unavailable")

        metadata = {
            "resolution_source": result.resolution_source,
            "model": result.model,
            "latency_ms": max(1, int((time.perf_counter() - started) * 1000)),
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "key_id": result.key_id,
            "fallback_attempts": result.fallback_attempts,
        }
        await asyncio.to_thread(
            db.save_turn,
            req.session_id,
            req.system_prompt or None,
            req.message,
            result.reply,
            metadata,
        )
        return {
            "session_id": req.session_id,
            "reply": result.reply,
            "metadata": metadata,
        }

    @app.get("/sessions/{session_id}/messages")
    async def session_messages(session_id: str):
        messages = await asyncio.to_thread(db.get_messages, session_id)
        if not messages:
            raise HTTPException(404, "session not found")
        return {"session_id": session_id, "messages": messages}

    return app


app = create_app()
