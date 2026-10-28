
import time

from app.tools import TOOL_REGISTRY, execute_tool


def slow_tool_for_test():
    """Simulate a tool that exceeds the timeout."""
    time.sleep(3)
    return "finished"


def test_slow_tool_returns_timeout_error(monkeypatch):
    monkeypatch.setitem(
        TOOL_REGISTRY,
        "slow_tool_for_test",
        slow_tool_for_test,
    )

    monkeypatch.setattr(
        "app.tools.get_settings",
        lambda: type("Settings", (), {"tool_timeout_seconds": 1})(),
    )

    result = execute_tool(
        tool_name="slow_tool_for_test",
        arguments={},
        step_id=1,
    )

    assert result.success is False
    assert "timed out" in (result.error or "").lower()
    assert result.error_type == "temporary"
