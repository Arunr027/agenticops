
from app.workflow import run_workflow


def test_addition_workflow_completes():
    result = run_workflow("add 10 and 20")

    assert result["status"] == "completed"
    assert result["final_answer"] == "30"
    assert len(result["tool_results"]) == 1
    assert result["tool_results"][0].success is True


def test_multiplication_workflow_completes():
    result = run_workflow("multiply 5 and 6")

    assert result["status"] == "completed"
    assert result["final_answer"] == "30"


def test_text_length_workflow_completes():
    result = run_workflow("length of AgenticOps")

    assert result["status"] == "completed"
    assert result["final_answer"] == "10"


def test_unsupported_task_fails_safely():
    result = run_workflow("send an email to my manager")

    assert result["status"] == "failed"
    assert result["tool_results"] == []
    assert result["errors"]


def test_step_limit_is_respected():
    result = run_workflow("add 10 and 20", max_steps=0)

    assert result["status"] == "failed"
    assert result["tool_results"] == []
    assert result["errors"]
