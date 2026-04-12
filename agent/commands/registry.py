from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent.commands import system_commands

CommandHandler = Callable[[dict[str, Any]], Any]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandHandler] = {
            "open_chrome": system_commands.open_chrome,
            "open_vscode": system_commands.open_vscode,
            "increase_volume": system_commands.increase_volume,
            "list_files": system_commands.list_files,
            "open_file": system_commands.open_file,
        }

    def get(self, command_name: str) -> CommandHandler | None:
        return self._commands.get(command_name)

    @staticmethod
    def normalize(command_name: str) -> str:
        candidate = command_name.strip().lower().replace("-", "_")
        aliases = {
            "open chrome": "open_chrome",
            "launch chrome": "open_chrome",
            "open vs code": "open_vscode",
            "open vscode": "open_vscode",
            "open cursor": "open_vscode",
            "volume up": "increase_volume",
        }
        return aliases.get(candidate, candidate)
