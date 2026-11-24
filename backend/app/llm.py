
"""LLM gateway: LiteLLM + key pool + failover + built-in cache."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import litellm
from litellm.caching import Cache

logger = logging.getLogger("gateway")

litellm.suppress_debug_info = True

ALLOWED_SIM_STATUSES = {429, 500, 502, 503}


class AllProvidersUnavailable(Exception):
    pass


@dataclass
class LLMResult:
    reply: str
    resolution_source: str
    model: str
    input_tokens: int
    output_tokens: int
    key_id: Optional[str]
    fallback_attempts: int


def parse_failure_header(value: str) -> dict:
    """'key_1=429,key_2=500' or '*=429' -> {'key_1': 429, ...}.
    Bad pairs are ignored."""

    result = {}

    for part in (value or "").split(","):
        name, _, status = part.partition("=")
        name = name.strip()
        status = status.strip()

        if name and status.isdigit() and int(status) in ALLOWED_SIM_STATUSES:
            result[name] = int(status)

    return result


class LLMGateway:

    def __init__(self, keys, model, timeout, max_tokens):
        self.keys = keys
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

        # LiteLLM built-in in-memory cache.
        # Cache key = model + full message list.
        litellm.cache = Cache(type="local")

    async def warmup(self):
        """Warm up LiteLLM using a mock response."""

        try:
            msgs = [{"role": "user", "content": "warmup"}]

            for _ in range(3):
                await self._call("mock-warmup", msgs, False)
                await asyncio.sleep(0.2)

        except Exception:
            logger.warning("warmup failed", exc_info=True)

        finally:
            # Remove warmup cache entries.
            litellm.cache = Cache(type="local")

    async def _call(self, api_key, messages, bypass_cache):
        """Call LiteLLM using the selected API key."""

        kwargs = dict(
            model=self.model,
            messages=messages,
            api_key=api_key,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            num_retries=0,
            caching=True,
        )

        # Skip cache when testing provider failover.
        if bypass_cache:
            kwargs["cache"] = {"no-cache": True}

        if api_key.startswith("mock"):
            # Offline demo/test mode.
            # Does not require a real API key.
            last = messages[-1]["content"]
            kwargs["mock_response"] = f"[mock reply] {last}"

        return await litellm.acompletion(**kwargs)

    async def complete(self, messages, simulate=None) -> LLMResult:

        simulate = simulate or {}

        # Simulated failures must bypass cache.
        bypass_cache = bool(simulate)

        failed = 0

        for index, key in enumerate(self.keys, start=1):

            key_id = f"key_{index}"

            status = simulate.get(key_id) or simulate.get("*")

            if status:
                logger.warning(
                    "%s: simulated HTTP %s",
                    key_id,
                    status
                )

                failed += 1
                continue

            try:
                response = await self._call(
                    key,
                    messages,
                    bypass_cache
                )

                reply = (
                    response.choices[0].message.content or ""
                ).strip()

                if not reply:
                    raise ValueError("empty reply")

            except Exception:
                logger.exception("%s failed", key_id)

                failed += 1
                continue

            # Check whether the response came from cache.
            hit = bool(
                getattr(response, "_hidden_params", {}).get("cache_hit")
            )

            usage = response.usage

            return LLMResult(
                reply=reply,
                resolution_source=(
                    "LLM_CACHE" if hit else "LIVE_INFERENCE"
                ),
                model=self.model,
                input_tokens=int(usage.prompt_tokens),
                output_tokens=int(usage.completion_tokens),
                key_id=None if hit else key_id,
                fallback_attempts=0 if hit else failed,
            )

        # All configured providers failed.
        raise AllProvidersUnavailable()
