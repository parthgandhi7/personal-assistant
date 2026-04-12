from __future__ import annotations

from fastapi import Header, HTTPException, status

from agent.core.config import get_settings


async def validate_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-api-key header",
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
