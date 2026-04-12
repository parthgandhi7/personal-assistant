from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class Settings(BaseModel):
    api_key: str = Field(..., description="API key required in x-api-key header")
    default_directory: Path = Field(default=Path.home(), description="Default directory for file operations")
    log_level: str = Field(default="INFO", description="Application log level")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and validate settings from environment variables once."""
    api_key = os.getenv("API_KEY")
    default_directory = Path(os.getenv("DEFAULT_DIRECTORY", str(Path.home()))).expanduser().resolve()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    try:
        settings = Settings(
            api_key=api_key,
            default_directory=default_directory,
            log_level=log_level,
        )
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc

    return settings
