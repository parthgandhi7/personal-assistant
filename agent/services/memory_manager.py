"""SQLite-backed memory accessor for planner prompt injection."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


class MemoryManager:
    """Fetch structured memory records for LLM planning.

    Expected schema:
    - aliases(alias TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at ...)
    - preferences(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at ...)
    - context(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at ...)

    The manager fails closed to empty dictionaries when tables are missing.
    """

    def __init__(self, db_path: str | None = None) -> None:
        raw_path = db_path or os.getenv("MEMORY_DB_PATH", "memory.db")
        self.db_path = Path(raw_path).expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _safe_fetch_map(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, str]:
        try:
            with self._connect() as connection:
                rows = connection.execute(query, params).fetchall()
        except sqlite3.Error:
            return {}

        result: dict[str, str] = {}
        for row in rows:
            key = str(row[0]).strip()
            value = str(row[1]).strip()
            if key and value:
                result[key] = value
        return result

    def fetch_aliases(self, limit: int = 20) -> dict[str, str]:
        """Return alias memory mapping alias -> resolved resource."""
        bounded_limit = max(1, min(limit, 100))
        query = (
            "SELECT alias, value FROM aliases "
            "ORDER BY COALESCE(updated_at, rowid) DESC "
            "LIMIT ?"
        )
        return self._safe_fetch_map(query, (bounded_limit,))

    def fetch_preferences(self) -> dict[str, str]:
        """Return user preference key/value memory."""
        return self._safe_fetch_map("SELECT key, value FROM preferences")

    def fetch_context(self) -> dict[str, str]:
        """Return contextual key/value memory."""
        return self._safe_fetch_map("SELECT key, value FROM context")

    def fetch_memory(self, alias_limit: int = 20) -> dict[str, dict[str, str]]:
        """Return all memory categories in a single structured payload."""
        return {
            "aliases": self.fetch_aliases(limit=alias_limit),
            "preferences": self.fetch_preferences(),
            "context": self.fetch_context(),
        }
