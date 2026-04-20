"""Validation helpers for LLM-generated execution plans."""

from __future__ import annotations

from typing import Any

ALLOWED_ACTIONS = {
    "open_application",
    "search_file",
    "open_file",
    "open_browser",
    "search_web",
    "increase_volume",
    "decrease_volume",
}

_ACTION_PARAM_RULES: dict[str, dict[str, type]] = {
    "open_application": {"application": str},
    "search_file": {"query": str},
    "open_file": {"path": str},
    "open_browser": {},
    "search_web": {"query": str},
    "increase_volume": {},
    "decrease_volume": {},
}

_OPTIONAL_PARAM_RULES: dict[str, dict[str, type]] = {
    "search_file": {"directory": str},
    "open_browser": {"browser": str},
    "increase_volume": {"amount": int},
    "decrease_volume": {"amount": int},
}


class PlanValidationError(ValueError):
    """Raised when generated plan fails safety or schema checks."""


def validate_plan(plan: dict[str, Any]) -> bool:
    """Validate plan structure and allowed actions.

    Args:
        plan: Parsed JSON plan from LLM.

    Returns:
        True when plan is valid.

    Raises:
        PlanValidationError: If plan is malformed or unsafe.
    """
    if not isinstance(plan, dict):
        raise PlanValidationError("Plan must be a JSON object")

    intent = plan.get("intent")
    if not isinstance(intent, str) or not intent.strip():
        raise PlanValidationError("'intent' must be a non-empty string")

    requires_confirmation = plan.get("requires_confirmation")
    if not isinstance(requires_confirmation, bool):
        raise PlanValidationError("'requires_confirmation' must be a boolean")

    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise PlanValidationError("'steps' must be a non-empty list")

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise PlanValidationError(f"Step {index} must be an object")

        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            raise PlanValidationError(f"Step {index} contains unknown action: {action}")

        parameters = step.get("parameters")
        if not isinstance(parameters, dict):
            raise PlanValidationError(f"Step {index} parameters must be an object")

        required = _ACTION_PARAM_RULES.get(action, {})
        optional = _OPTIONAL_PARAM_RULES.get(action, {})

        for key, expected_type in required.items():
            value = parameters.get(key)
            if not isinstance(value, expected_type) or (isinstance(value, str) and not value.strip()):
                raise PlanValidationError(
                    f"Step {index} action '{action}' requires parameter '{key}' of type {expected_type.__name__}"
                )

        allowed_param_keys = set(required) | set(optional)
        unexpected = set(parameters.keys()) - allowed_param_keys
        if unexpected:
            raise PlanValidationError(
                f"Step {index} action '{action}' has unsupported parameters: {sorted(unexpected)}"
            )

        for key, expected_type in optional.items():
            if key in parameters and not isinstance(parameters[key], expected_type):
                raise PlanValidationError(
                    f"Step {index} action '{action}' optional parameter '{key}' must be {expected_type.__name__}"
                )

    return True
