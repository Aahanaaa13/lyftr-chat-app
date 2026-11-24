import os
from dataclasses import dataclass

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer clearly and keep answers short."
)


@dataclass(frozen=True)
class Settings:
    api_keys: list
    model: str
    database_url: str
    allowed_origins: list
    enable_failure_simulation: bool
    default_system_prompt: str
    request_timeout: float
    max_tokens: int

    @property
    def db_path(self) -> str:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("DATABASE_URL must start with sqlite:///")
        # sqlite:////data/app.db -> /data/app.db ; sqlite:///app.db -> app.db
        return self.database_url[len(prefix):]


def _split(value: str) -> list:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_settings() -> Settings:
    return Settings(
        api_keys=_split(os.getenv("LLM_API_KEYS", "")),
        model=os.getenv("LLM_MODEL", "gemini/gemini-3.5-flash-lite"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./app.db"),
        allowed_origins=_split(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
        ),
        enable_failure_simulation=os.getenv(
            "ENABLE_FAILURE_SIMULATION", "false"
        ).lower()
        == "true",
        default_system_prompt=os.getenv(
            "DEFAULT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT
        ),
        request_timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
    )
