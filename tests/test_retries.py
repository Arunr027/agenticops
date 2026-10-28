
from app.models import PlanStep, ToolResult
from app.workflow import executor_node


def make_state():
    return {
        "task": "Add 15 and 27",
        "session_id": "retry-test",
        "max_steps": 5,
        "max_retries": 2,
        "retry_count": 0,
        "retry_pending": False,
        "last_error": "",
        "plan": [
            PlanStep(
                step_id=1,
                description="Add 15 and 27",
                tool_name="add_numbers",
                arguments={"a": 15, "b": 27},
            )
        ],
        "current_step": 0,
        "tool_results": [],
        "errors": [],
        "status": "running",
        "final_answer": "",
    }


def test_temporary_failure_requests_retry(monkeypatch):
    
    def fake_execute_tool(**kwargs):
        return ToolResult(
            step_id=1,
            tool_name="add_numbers",
            success=False,
            error="Temporary service error",
            error_type="temporary",
        )


    monkeypatch.setattr(
        "app.workflow.execute_tool", fake_execute_tool
    )

    result = executor_node(make_state())

    assert result["retry_pending"] is True
    assert result["retry_count"] == 1
    assert result["current_step"] == 0
    assert result["status"] == "running"


def test_successful_retry_advances_step(monkeypatch):
    def fake_execute_tool(**kwargs):
        return ToolResult(
            step_id=1,
            tool_name="add_numbers",
            success=True,
            output=42,
        )

    monkeypatch.setattr(
        "app.workflow.execute_tool", fake_execute_tool
    )

    state = make_state()
    state["retry_count"] = 1
    state["retry_pending"] = True

    result = executor_node(state)

    assert result["retry_pending"] is False
    assert result["retry_count"] == 0
    assert result["current_step"] == 1
    assert result["tool_results"][-1].output == 42


def test_permanent_error_does_not_retry(monkeypatch):
    def fake_execute_tool(**kwargs):
        return ToolResult(
            step_id=1,
            tool_name="add_numbers",
            success=False,
            error="a must be a number",
            error_type="permanent",
        )

    monkeypatch.setattr(
        "app.workflow.execute_tool", fake_execute_tool
    )

    result = executor_node(make_state())

    assert result["retry_pending"] is False
    assert result["retry_count"] == 0
    assert result["status"] == "failed"
    assert result["errors"]


def test_retry_limit_is_respected(monkeypatch):
    def fake_execute_tool(**kwargs):
        return ToolResult(
            step_id=1,
            tool_name="add_numbers",
            success=False,
            error="Temporary service error",
            error_type="temporary",
        )

    monkeypatch.setattr(
        "app.workflow.execute_tool", fake_execute_tool
    )

    state = make_state()
    state["retry_count"] = 2

    result = executor_node(state)

    assert result["retry_pending"] is False
    assert result["retry_count"] == 0
    assert result["status"] == "failed"
    assert result["errors"]
