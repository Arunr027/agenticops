
from app.tools import (
    add_numbers,
    execute_tool,
    get_text_length,
    multiply_numbers,
)


def test_add_numbers():
    assert add_numbers(10, 20) == 30


def test_multiply_numbers():
    assert multiply_numbers(5, 6) == 30


def test_get_text_length():
    assert get_text_length("AgenticOps") == 10


def test_execute_tool_returns_structured_result():
    result = execute_tool(
        tool_name="add_numbers",
        arguments={"a": 10, "b": 20},
        step_id=2,
    )

    assert result.success is True
    assert result.output == 30
    assert result.step_id == 2


def test_unknown_tool_is_rejected():
    result = execute_tool(
        tool_name="delete_everything",
        arguments={},
    )

    assert result.success is False
    assert result.error == "Unknown tool: delete_everything"


def test_invalid_number_returns_failure():
    result = execute_tool(
        tool_name="add_numbers",
        arguments={"a": "ten", "b": 20},
    )

    assert result.success is False
    assert result.error == "a must be a number"


def test_missing_argument_returns_failure():
    result = execute_tool(
        tool_name="add_numbers",
        arguments={"a": 10},
    )

    assert result.success is False
    assert result.error is not None
