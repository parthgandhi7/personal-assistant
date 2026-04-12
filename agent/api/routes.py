from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from agent.core.security import validate_api_key
from agent.services.executor import CommandExecutionError, CommandExecutor

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


@router.post("/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    _: None = Depends(validate_api_key),
    executor: CommandExecutor = Depends(get_executor),
) -> CommandResponse:
    try:
        result = executor.execute(request.command, request.args)
    except CommandExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if isinstance(result, dict):
        return CommandResponse(status="success", message="Command executed", data=result)

    return CommandResponse(status="success", message=str(result), data=None)
