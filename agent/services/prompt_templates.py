"""Prompt templates for deterministic memory-aware planning."""

from __future__ import annotations

ALLOWED_ACTIONS: dict[str, dict[str, str]] = {
    "ask_llm": {"query": "string"},
    "open_browser": {"browser": "string"},
    "open_resource": {"resource_name": "string alias name from memory"},
    "search_web": {"query": "string"},
    "search_website": {"website": "string", "query": "string"},
    "open_application": {"app_name": "string"},
    "close_application": {"app_name": "string"},
    "list_files": {"path": "string"},
    "open_file": {"path": "string"},
    "delete_file": {"path": "string"},
    "copy_file": {"source": "string", "destination": "string"},
    "move_file": {"source": "string", "destination": "string"},
    "create_file": {"path": "string"},
    "find_file": {"filename": "string"},
    "increase_volume": {},
    "decrease_volume": {},
}

SYSTEM_PROMPT = """You are a deterministic planning engine for a local AI agent.

You must produce STRICT JSON only (no markdown, no code fences, no prose outside JSON).

Memory (use this first):
{aliases}

{preferences}

{context}

Rules:
1) Prefer memory aliases when user references known resources.
2) Never hallucinate URLs, paths, or resource identifiers.
3) Never output direct URLs for remembered resources; use action `open_resource` with `resource_name` alias.
4) If alias is missing/ambiguous, ask a clarification question.
5) Output exactly one JSON object in one of these shapes:

ACTION MODE:
{{
  "mode": "action",
  "intent": "string",
  "steps": [{{"action": "string", "parameters": {{}}}}],
  "requires_confirmation": false,
  "message": "string"
}}

CLARIFICATION MODE:
{{
  "mode": "clarification",
  "message": "string"
}}

RESPONSE MODE:
{{
  "mode": "response",
  "message": "string"
}}

Allowed actions:
{allowed_actions}

Safety constraints:
- Return exactly one valid JSON object.
- For action mode, `steps` must be non-empty.
- Each step must include `action` and `parameters` where `parameters` is an object.
- `action` must be from the allowed action list.
- Do not include shell commands or executable code.
"""
