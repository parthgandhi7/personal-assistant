"""LLM-backed strict planner with structured memory injection."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from agent.core.config import get_settings
from agent.services.memory_manager import MemoryManager
from agent.services.prompt_templates import ALLOWED_ACTIONS, SYSTEM_PROMPT
from agent.services.validation import PlanValidationError, validate_plan

DEFAULT_MODEL = "gpt-4.1-mini"

logger = logging.getLogger(__name__)


class PlannerOutputError(RuntimeError):
    """Raised when planner output cannot be parsed/validated after retries."""


def _extract_json_object(content: str) -> dict[str, Any]:
    """Extract a JSON object from text content defensively."""
    text = content.strip()
    if not text:
        raise ValueError("Empty model response")

    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

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


def _format_section(title: str, values: dict[str, str]) -> str:
    if not values:
        return f"{title}:\n- (none)"

    lines = [f"{title}:"]
    for key, value in values.items():
        lines.append(f"- {key} -> {value}")
    return "\n".join(lines)


def format_aliases(aliases: dict[str, str]) -> str:
    """Format alias memory as bullet list text."""
    return _format_section("Aliases", aliases)


def format_preferences(preferences: dict[str, str]) -> str:
    """Format user preferences as bullet list text."""
    return _format_section("Preferences", preferences)


def format_context(context: dict[str, str]) -> str:
    """Format contextual memory as bullet list text."""
    return _format_section("Context", context)


def _build_system_prompt(memory: dict[str, dict[str, str]]) -> str:
    allowed_actions = "\n".join(f"- {name}: {schema}" for name, schema in ALLOWED_ACTIONS.items())
    return SYSTEM_PROMPT.format(
        aliases=format_aliases(memory.get("aliases", {})),
        preferences=format_preferences(memory.get("preferences", {})),
        context=format_context(memory.get("context", {})),
        allowed_actions=allowed_actions,
    )


def _create_completion(client: OpenAI, model: str, system_prompt: str, user_input: str) -> str:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def generate_plan(user_input: str) -> dict[str, Any]:
    """Generate and validate a strict execution plan from user text."""
    normalized_input = user_input.strip()
    if not normalized_input:
        return _error_response("User input must be a non-empty string", retryable=False)

    settings = get_settings()
    if not settings.openai_api_key:
        return _error_response("Missing OPENAI_API_KEY", retryable=False)

    model = settings.openai_model or DEFAULT_MODEL
    client = OpenAI(api_key=settings.openai_api_key)

    memory_manager = MemoryManager()
    memory = memory_manager.fetch_memory()
    system_prompt = _build_system_prompt(memory)
    memory_used = any(memory.get(bucket) for bucket in ("aliases", "preferences", "context"))

    logger.info("planner_input", extra={"user_input": normalized_input})

    parse_errors = (json.JSONDecodeError, ValueError)
    for attempt in range(2):
        try:
            content = _create_completion(client, model, system_prompt, normalized_input)
            plan = _extract_json_object(content)
            validate_plan(plan)

            logger.info(
                "planner_output",
                extra={
                    "generated_plan": plan,
                    "memory_used": memory_used,
                    "attempt": attempt + 1,
                },
            )
            return plan
        except parse_errors as exc:
            if attempt == 1:
                raise PlannerOutputError(f"Planner response is not valid JSON: {exc}") from exc
            logger.warning("planner_json_parse_retry", extra={"error": str(exc), "attempt": attempt + 1})
        except PlanValidationError as exc:
            return _error_response(f"Invalid planner output: {exc}", retryable=False)
        except PlannerOutputError as exc:
            return _error_response(str(exc), retryable=False)
        except Exception as exc:
            if attempt == 1:
                return _error_response(f"Failed to generate plan: {exc}", retryable=True)
            logger.warning("planner_request_retry", extra={"error": str(exc), "attempt": attempt + 1})

    return _error_response("Failed to generate plan", retryable=True)
