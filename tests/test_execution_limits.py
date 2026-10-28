
from app.models import PlanStep, WorkflowPlan
from app.workflow import planner_node


def test_planner_rejects_plan_over_max_steps(monkeypatch):
    def fake_generate_plan(task, max_steps):
        return WorkflowPlan(
            goal=task,
            steps=[
                PlanStep(
                    step_id=1,
                    description="First addition",
                    tool_name="add_numbers",
                    arguments={"a": 1, "b": 2},
                ),
                PlanStep(
                    step_id=2,
                    description="Second addition",
                    tool_name="add_numbers",
                    arguments={"a": 3, "b": 4},
                ),
            ],
        )

    monkeypatch.setattr(
        "app.workflow.generate_plan",
        fake_generate_plan,
    )

    result = planner_node(
        {
            "task": "Perform two additions",
            "max_steps": 1,
        }
    )

    assert result["status"] == "failed"
    assert result["plan"] == []
    assert any(
        "step limit" in error.lower()
        for error in result["errors"]
    )


def test_planner_rejects_zero_max_steps():
    result = planner_node(
        {
            "task": "Add 1 and 2",
            "max_steps": 0,
        }
    )

    assert result["status"] == "failed"
    assert result["plan"] == []
    assert any(
        "max_steps must be at least 1" in error
        for error in result["errors"]
    )
