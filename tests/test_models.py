
import pytest
from pydantic import ValidationError

from app.models import (
    PlanStep,
    ToolResult,
    WorkflowPlan,
    WorkflowRequest,
    WorkflowResponse,
)


def test_workflow_request_defaults():
    request = WorkflowRequest(task="Calculate total expenses")

    assert request.task == "Calculate total expenses"
    assert request.max_steps == 5
    assert request.session_id is None


def test_workflow_request_rejects_excessive_steps():
    with pytest.raises(ValidationError):
        WorkflowRequest(task="Test task", max_steps=50)


def test_plan_step_accepts_tool_arguments():
    step = PlanStep(
        step_id=1,
        description="Add two numbers",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
    )

    assert step.arguments["a"] == 10
    assert step.arguments["b"] == 20


def test_workflow_plan_contains_steps():
    step = PlanStep(
        step_id=1,
        description="Add two numbers",
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
    )

    plan = WorkflowPlan(
        goal="Calculate the sum",
        steps=[step],
    )

    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "add_numbers"


def test_tool_result_records_success():
    result = ToolResult(
        step_id=1,
        tool_name="add_numbers",
        success=True,
        output=30,
    )

    assert result.success is True
    assert result.output == 30


def test_workflow_response_accepts_completed_status():
    response = WorkflowResponse(
        session_id="test-session",
        status="completed",
        answer="The total is 30.",
        steps_executed=1,
    )

    assert response.status == "completed"
    assert response.answer == "The total is 30."
    assert response.errors == []

