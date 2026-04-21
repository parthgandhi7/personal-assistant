from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from agent.core.security import validate_api_key
from agent.services.executor import CommandExecutionError, CommandExecutor
from agent.services.llm_planner import generate_plan

router = APIRouter()


class CommandRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Command name or natural-language command")
    args: dict[str, Any] = Field(default_factory=dict, description="Command-specific arguments")


class CommandResponse(BaseModel):
    status: str
    message: str
    data: Any | None = None


def get_executor(request: Request) -> CommandExecutor:
    executor = getattr(request.app.state, "executor", None)
    if executor is None:
        raise HTTPException(status_code=500, detail="Command executor not initialized")
    return executor


def _execute_plan(executor: CommandExecutor, plan: dict[str, Any]) -> dict[str, Any]:
    requires_confirmation = bool(plan.get("requires_confirmation", False))
    if requires_confirmation:
        return {
            "intent": plan.get("intent"),
            "requires_confirmation": True,
            "steps": plan.get("steps", []),
            "step_results": [],
            "executed": False,
        }

    step_results: list[dict[str, Any]] = []
    for index, step in enumerate(plan.get("steps", [])):
        action = step.get("action")
        parameters = step.get("parameters", {})
        result = executor.execute(str(action), parameters)
        step_results.append(
            {
                "index": index,
                "action": action,
                "result": result,
            }
        )

    return {
        "intent": plan.get("intent"),
        "requires_confirmation": False,
        "steps": plan.get("steps", []),
        "step_results": step_results,
        "executed": True,
    }


@router.post("/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    _: None = Depends(validate_api_key),
    executor: CommandExecutor = Depends(get_executor),
) -> CommandResponse:
    try:
        result = executor.execute(request.command, request.args)
    except CommandExecutionError as exc:
        is_unknown_command = str(exc).startswith("Unknown command:")
        if not is_unknown_command:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        plan = generate_plan(request.command)
        if "error" in plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=plan["error"]["message"],
            )

        try:
            planned_result = _execute_plan(executor, plan)
        except CommandExecutionError as plan_exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan execution failed: {plan_exc}",
            ) from plan_exc

        return CommandResponse(status="success", message="Plan executed", data=planned_result)

    if isinstance(result, dict):
        return CommandResponse(status="success", message="Command executed", data=result)

    return CommandResponse(status="success", message=str(result), data=None)
