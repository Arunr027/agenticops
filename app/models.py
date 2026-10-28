
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    task: str = Field(min_length=1, max_length=5000)
    session_id: str | None = None
    max_steps: int = Field(default=5, ge=1, le=10)


class PlanStep(BaseModel):
    step_id: int = Field(ge=1)
    description: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class WorkflowPlan(BaseModel):
    goal: str = Field(min_length=1)
    steps: list[PlanStep] = Field(max_length=10)



class ToolResult(BaseModel):
    step_id: int = Field(ge=1)
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    error_type: Literal[
        "permanent",
        "temporary",
    ] | None = None
    duration_ms: float = Field(default=0.0, ge=0)



class WorkflowResponse(BaseModel):
    session_id: str
    status: Literal["completed", "failed", "running"]
    answer: str
    steps_executed: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)
