from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class Settings(BaseModel):
    api_key: str = Field(..., description="API key required in x-api-key header")
    default_directory: Path = Field(default=Path.home(), description="Default directory for file operations")
    log_level: str = Field(default="INFO", description="Application log level")
    telegram_bot_token: str | None = Field(default=None, description="Telegram bot token used for long polling")
    telegram_command_url: str = Field(
        default="http://127.0.0.1:8000/command",
        description="HTTP endpoint that receives command requests from the Telegram bridge",
    )
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for LLM planner")
    openai_model: str = Field(default="gpt-4.1-mini", description="OpenAI model used by LLM planner")


def _load_dotenv_if_present() -> None:
    """Load key/value pairs from a local .env file into os.environ when unset."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and validate settings from environment variables once."""
    _load_dotenv_if_present()
    api_key = os.getenv("API_KEY")
    default_directory = Path(os.getenv("DEFAULT_DIRECTORY", str(Path.home()))).expanduser().resolve()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    try:
        settings = Settings(
            api_key=api_key,
            default_directory=default_directory,
            log_level=log_level,
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_command_url=os.getenv("TELEGRAM_COMMAND_URL", "http://127.0.0.1:8000/command"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        )
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc

    return settings
