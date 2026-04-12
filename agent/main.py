from __future__ import annotations

import logging

from fastapi import FastAPI

from agent.api.routes import router as command_router
from agent.commands.registry import CommandRegistry
from agent.core.config import get_settings
from agent.services.executor import CommandExecutor


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Personal AI Laptop Agent", version="0.1.0")
    app.state.executor = CommandExecutor(CommandRegistry())
    app.include_router(command_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
