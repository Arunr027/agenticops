
from typing import Literal, TypedDict

from app.models import PlanStep, ToolResult


class WorkflowState(TypedDict, total=False):
    task: str
    session_id: str
    max_steps: int
    max_retries: int
    retry_count: int
    plan: list[PlanStep]
    current_step: int
    tool_results: list[ToolResult]
    final_answer: str
    errors: list[str]
    status: Literal["pending", "running", "completed", "failed"]
    retry_pending: bool
    last_error: str