
from app.models import ToolResult
from app.workflow import build_workflow


def test_workflow_retries_temporary_failure(monkeypatch):
    attempts = {"count": 0}

    def fake_execute_tool(**kwargs):
        attempts["count"] += 1

        # First attempt: simulate a temporary failure.
        if attempts["count"] == 1:
            return ToolResult(
                step_id=kwargs["step_id"],
                tool_name=kwargs["tool_name"],
                success=False,
                error="Temporary service error",
                error_type="temporary",
            )

        # Second attempt: simulate success.
        return ToolResult(
            step_id=kwargs["step_id"],
            tool_name=kwargs["tool_name"],
            success=True,
            output=42,
        )

    def fake_generate_plan(task, max_steps):
        from app.models import PlanStep

        return [
            PlanStep(
                step_id=1,
                description="Add 15 and 27",
                tool_name="add_numbers",
                arguments={"a": 15, "b": 27},
            )
        ]

    # Replace the real tool and planner with test versions.
    monkeypatch.setattr(
        "app.workflow.execute_tool",
        fake_execute_tool,
    )
    monkeypatch.setattr(
        "app.workflow.generate_plan",
        fake_generate_plan,
    )

    # Build the workflow without a Redis checkpointer.
    app = build_workflow()

    # Provide the initial workflow state.
    result = app.invoke(
        {
            "task": "Add 15 and 27",
            "session_id": "integration-retry-test",
            "max_steps": 5,
            "max_retries": 2,
            "retry_count": 0,
            "retry_pending": False,
            "last_error": "",
            "plan": [],
            "current_step": 0,
            "tool_results": [],
            "errors": [],
            "status": "pending",
            "final_answer": "",
        }
    )

    # Confirm the workflow retried and then succeeded.
    assert attempts["count"] == 2
    assert result["status"] == "completed"
    assert result["current_step"] == 1
    assert result["tool_results"][-1].output == 42
