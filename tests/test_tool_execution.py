
from app.tools import execute_tool


def test_add_numbers_executes_successfully():
    result = execute_tool("add_numbers", {"a": 15, "b": 27})

    assert result.success is True
    assert result.output == 42


def test_multiply_numbers_executes_successfully():
    result = execute_tool("multiply_numbers", {"a": 6, "b": 7})

    assert result.success is True
    assert result.output == 42


def test_get_text_length_executes_successfully():
    result = execute_tool("get_text_length", {"text": "AgenticOps"})

    assert result.success is True
    assert result.output == 10


def test_unknown_tool_returns_permanent_error():
    result = execute_tool("unknown_tool", {})

    assert result.success is False
    assert result.error_type == "permanent"
    assert "Unknown tool" in (result.error or "")


def test_invalid_number_returns_permanent_error():
    result = execute_tool("add_numbers", {"a": "fifteen", "b": 27})

    assert result.success is False
    assert result.error_type == "permanent"
