from __future__ import annotations

import logging
from typing import Any

from agent.commands.registry import CommandRegistry

logger = logging.getLogger(__name__)


class CommandExecutionError(Exception):
    """Raised when a command cannot be executed."""


class CommandExecutor:
    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry

    def execute(self, command_name: str, payload: dict[str, Any]) -> Any:
        normalized_name = self.registry.normalize(command_name)
        handler = self.registry.get(normalized_name)

        if handler is None:
            raise CommandExecutionError(f"Unknown command: {command_name}")

        logger.info(
            "executing_command",
            extra={
                "command": normalized_name,
                "payload_keys": list(payload.keys()),
            },
        )

        try:
            result = handler(payload)
        except Exception as exc:
            logger.exception("command_failed", extra={"command": normalized_name})
            raise CommandExecutionError(str(exc)) from exc

        logger.info("command_succeeded", extra={"command": normalized_name})
        return result
