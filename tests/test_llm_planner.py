
from unittest.mock import MagicMock, patch

import pytest

from app.models import WorkflowPlan, PlanStep
from app.llm_planner import generate_plan


def valid_plan():
    return WorkflowPlan(
        goal="Add two numbers",
        steps=[
            PlanStep(
                step_id=1,
                description="Add 10 and 20",
                tool_name="add_numbers",
                arguments={"a": 10, "b": 20},
            )
        ],
    )


@patch("app.llm_planner.genai.Client")
@patch("app.llm_planner.get_settings")
def test_generate_plan_accepts_valid_plan(mock_settings, mock_client):
    mock_settings.return_value.gemini_api_key = "test-key"
    mock_settings.return_value.gemini_model = "gemini-3.5-flash"

    client = mock_client.return_value
    client.models.generate_content.return_value.parsed = valid_plan()

    plan = generate_plan("Add 10 and 20")

    assert plan.steps[0].tool_name == "add_numbers"
    assert plan.steps[0].arguments == {"a": 10, "b": 20}


@patch("app.llm_planner.genai.Client")
@patch("app.llm_planner.get_settings")
def test_generate_plan_rejects_unknown_tool(mock_settings, mock_client):
    mock_settings.return_value.gemini_api_key = "test-key"
    mock_settings.return_value.gemini_model = "gemini-3.5-flash"

    bad_plan = WorkflowPlan(
        goal="Run an unknown tool",
        steps=[
            PlanStep(
                step_id=1,
                description="Run a tool",
                tool_name="execute_arbitrary_code",
                arguments={},
            )
        ],
    )

    mock_client.return_value.models.generate_content.return_value.parsed = (
        bad_plan
    )

    with pytest.raises(ValueError, match="unregistered tool"):
        generate_plan("Run an unknown tool")


@patch("app.llm_planner.genai.Client")
@patch("app.llm_planner.get_settings")
def test_generate_plan_rejects_too_many_steps(
    mock_settings, mock_client
):
    mock_settings.return_value.gemini_api_key = "test-key"
    mock_settings.return_value.gemini_model = "gemini-3.5-flash"

    plan = WorkflowPlan(
        goal="Multiple operations",
        steps=[
            PlanStep(
                step_id=i,
                description="Add two numbers",
                tool_name="add_numbers",
                arguments={"a": 1, "b": 2},
            )
            for i in range(1, 4)
        ],
    )

    mock_client.return_value.models.generate_content.return_value.parsed = (
        plan
    )

    with pytest.raises(ValueError, match="maximum of 2 steps"):
        generate_plan("Perform several operations", max_steps=2)
