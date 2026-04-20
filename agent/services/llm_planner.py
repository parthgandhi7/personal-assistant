"""LLM-backed strict planner: natural language -> validated execution JSON."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from agent.core.config import get_settings
from agent.services.prompt_templates import SYSTEM_PROMPT, build_user_prompt
from agent.services.validation import PlanValidationError, validate_plan

DEFAULT_MODEL = "gpt-4.1-mini"


def _extract_json_object(content: str) -> dict[str, Any]:
    """Extract a JSON object from text content defensively."""
    text = content.strip()

    # Fast path: already raw JSON object.
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    # Defensive fallback: find first object boundaries.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")

    return json.loads(text[start : end + 1])


def _error_response(message: str, retryable: bool = False) -> dict[str, Any]:
    """Return a structured safe error payload."""
    return {
        "error": {
            "type": "planner_error",
            "message": message,
            "retryable": retryable,
        }
    }


def _build_messages(user_input: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(user_input)},
    ]


def generate_plan(user_input: str) -> dict[str, Any]:
    """Generate and validate a strict execution plan from user text.

    Args:
        user_input: Raw natural-language request.

    Returns:
        Validated plan dictionary on success, or structured error payload.
    """
    normalized_input = user_input.strip()
    if not normalized_input:
        return _error_response("User input must be a non-empty string", retryable=False)

    settings = get_settings()
    if not settings.openai_api_key:
        return _error_response("Missing OPENAI_API_KEY", retryable=False)

    model = settings.openai_model or DEFAULT_MODEL
    client = OpenAI(api_key=settings.openai_api_key)
    messages = _build_messages(normalized_input)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=messages,
            )
            content = (response.choices[0].message.content or "").strip()
            plan = _extract_json_object(content)
            validate_plan(plan)
            return plan
        except (json.JSONDecodeError, PlanValidationError, ValueError) as exc:
            # Unsafe or malformed LLM output: do not retry endlessly, fail closed.
            return _error_response(f"Invalid planner output: {exc}", retryable=False)
        except Exception as exc:  # API/network/provider failures.
            last_error = exc
            if attempt == 1:
                break

    return _error_response(f"Failed to generate plan: {last_error}", retryable=True)
