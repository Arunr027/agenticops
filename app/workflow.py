
import logging
import re
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.llm_planner import generate_plan
from app.models import PlanStep
from app.state import WorkflowState
from app.tools import execute_tool

logger = logging.getLogger("agenticops.workflow")


def _parse_number(value: str) -> int | float:
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def _deterministic_plan(task: str) -> list[PlanStep]:
    """Create a local plan for supported tasks without an LLM."""
    plan: list[PlanStep] = []

    addition = re.search(
        r"\badd\s+(-?\d+(?:\.\d+)?)\s+(?:and|plus)\s+(-?\d+(?:\.\d+)?)\b",
        task,
        re.IGNORECASE,
    )
    multiplication = re.search(
        r"\bmultiply\s+(-?\d+(?:\.\d+)?)\s+(?:and|by)\s+(-?\d+(?:\.\d+)?)\b",
        task,
        re.IGNORECASE,
    )
    text_length = re.search(
        r"\b(?:length of|count characters in)\s+(.+?)\s*$",
        task,
        re.IGNORECASE,
    )

    if addition:
        a, b = map(_parse_number, addition.groups())
        plan.append(
            PlanStep(
                step_id=1,
                description=f"Add {a} and {b}",
                tool_name="add_numbers",
                arguments={"a": a, "b": b},
            )
        )
    elif multiplication:
        a, b = map(_parse_number, multiplication.groups())
        plan.append(
            PlanStep(
                step_id=1,
                description=f"Multiply {a} and {b}",
                tool_name="multiply_numbers",
                arguments={"a": a, "b": b},
            )
        )
    elif text_length:
        text = text_length.group(1).strip().strip("\"'")
        if text:
            plan.append(
                PlanStep(
                    step_id=1,
                    description=f"Count characters in {text}",
                    tool_name="get_text_length",
                    arguments={"text": text},
                )
            )

    return plan


def planner_node(state: WorkflowState) -> dict[str, Any]:
    """Use Gemini first, with a deterministic fallback."""
    task = state.get("task", "").strip()
    max_steps = state.get("max_steps", 5)

    logger.info("Planner started | max_steps=%s", max_steps)

    if max_steps < 1:
        logger.warning("Planning rejected | reason=invalid_max_steps")
        return {
            "plan": [],
            "current_step": 0,
            "tool_results": [],
            "errors": ["max_steps must be at least 1."],
            "status": "failed",
            "final_answer": "",
        }

    planning_errors: list[str] = []

    try:
        llm_plan = generate_plan(task, max_steps=max_steps)

        logger.info(
            "Gemini planner returned %s step(s)",
            len(llm_plan.steps),
        )

        if llm_plan.steps:
            if len(llm_plan.steps) > max_steps:
                logger.warning(
                    "Planning rejected | reason=step_limit_exceeded "
                    "| planned_steps=%s | max_steps=%s",
                    len(llm_plan.steps),
                    max_steps,
                )
                return {
                    "plan": [],
                    "current_step": 0,
                    "tool_results": [],
                    "errors": [
                        "The plan exceeds the configured step limit."
                    ],
                    "status": "failed",
                    "final_answer": "",
                }

            logger.info("Planner selected Gemini plan")

            return {
                "plan": llm_plan.steps,
                "current_step": 0,
                "tool_results": [],
                "errors": [],
                "status": "running",
                "final_answer": "",
            }

        logger.warning(
            "Gemini returned an empty plan; trying deterministic fallback"
        )
        planning_errors.append(
            f"Gemini could not create a plan: {llm_plan.goal}"
        )

    except Exception as exc:
        # Keep supported local tasks usable during API outages.
        logger.warning(
            "Gemini planning failed; trying deterministic fallback "
            "| error_type=%s",
            type(exc).__name__,
        )
        planning_errors.append(
            f"Gemini planning unavailable: {type(exc).__name__}: {exc}"
        )

    plan = _deterministic_plan(task)

    logger.info(
        "Deterministic fallback produced %s step(s)",
        len(plan),
    )

    if plan:
        if len(plan) > max_steps:
            logger.warning(
                "Fallback plan rejected | reason=step_limit_exceeded"
            )
            return {
                "plan": [],
                "current_step": 0,
                "tool_results": [],
                "errors": ["The plan exceeds the configured step limit."],
                "status": "failed",
                "final_answer": "",
            }

        logger.info("Planner selected deterministic fallback")

        return {
            "plan": plan,
            "current_step": 0,
            "tool_results": [],
            "errors": [],
            "status": "running",
            "final_answer": "",
        }

    logger.error("Planning failed | no supported plan available")

    return {
        "plan": [],
        "current_step": 0,
        "tool_results": [],
        "errors": planning_errors
        + ["The task could not be planned using available tools."],
        "status": "failed",
        "final_answer": "",
    }


def executor_node(state: WorkflowState) -> dict[str, Any]:
    """Execute a planned step with bounded retries."""

    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    session_id = state.get("session_id", "unknown")

    if current_step >= len(plan):
        logger.error(
            "Executor has no step to execute | session_id=%s",
            session_id,
        )
        return {
            "errors": state.get("errors", [])
            + ["No planned step is available to execute."],
            "status": "failed",
            "retry_pending": False,
        }

    step = plan[current_step]

    logger.info(
        "Executing tool | session_id=%s | step_id=%s "
        "| tool=%s | attempt=%s",
        session_id,
        step.step_id,
        step.tool_name,
        retry_count + 1,
    )

    result = execute_tool(
        tool_name=step.tool_name,
        arguments=step.arguments,
        step_id=step.step_id,
    )

    if result.success:
        logger.info(
            "Tool execution succeeded | session_id=%s "
            "| step_id=%s | tool=%s",
            session_id,
            step.step_id,
            step.tool_name,
        )
        return {
            "tool_results": state.get("tool_results", []) + [result],
            "current_step": current_step + 1,
            "retry_count": 0,
            "retry_pending": False,
            "last_error": "",
            "status": "running",
        }

    error_message = result.error or "Tool execution failed."
    temporary_error = result.error_type == "temporary"

    if temporary_error and retry_count < max_retries:
        logger.warning(
            "Temporary tool failure; scheduling retry "
            "| session_id=%s | step_id=%s | tool=%s "
            "| retry=%s/%s | error=%s",
            session_id,
            step.step_id,
            step.tool_name,
            retry_count + 1,
            max_retries,
            error_message,
        )
        return {
            "current_step": current_step,
            "tool_results": state.get("tool_results", []),
            "retry_count": retry_count + 1,
            "retry_pending": True,
            "last_error": error_message,
            "status": "running",
        }

    logger.error(
        "Tool execution failed permanently or retry limit reached "
        "| session_id=%s | step_id=%s | tool=%s "
        "| error_type=%s | error=%s",
        session_id,
        step.step_id,
        step.tool_name,
        result.error_type,
        error_message,
    )

    return {
        "tool_results": state.get("tool_results", []) + [result],
        "current_step": current_step + 1,
        "retry_count": 0,
        "retry_pending": False,
        "last_error": error_message,
        "errors": state.get("errors", []) + [error_message],
        "status": "failed",
    }


def route_after_execution(state: WorkflowState) -> str:
    """Retry the current step or send its result to verification."""
    if state.get("retry_pending", False):
        return "retry"
    return "verify"


def verifier_node(state: WorkflowState) -> dict[str, Any]:
    """Check tool results and determine the workflow outcome."""
    errors = state.get("errors", [])
    results = state.get("tool_results", [])
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    session_id = state.get("session_id", "unknown")

    logger.info(
        "Verifier started | session_id=%s | completed_steps=%s/%s",
        session_id,
        current_step,
        len(plan),
    )

    if errors:
        logger.error(
            "Verification failed | session_id=%s | error_count=%s",
            session_id,
            len(errors),
        )
        return {
            "status": "failed",
            "final_answer": "Workflow failed: " + "; ".join(errors),
        }

    if not results or not results[-1].success:
        logger.error(
            "Verification failed | session_id=%s "
            "| reason=no_successful_tool_result",
            session_id,
        )
        return {
            "status": "failed",
            "final_answer": "Workflow failed: no successful tool result.",
            "errors": ["No successful tool result was available."],
        }

    if current_step < len(plan):
        logger.info(
            "Verification passed for current step; more steps remain "
            "| session_id=%s",
            session_id,
        )
        return {"status": "running"}

    logger.info(
        "Verification passed | session_id=%s | status=completed",
        session_id,
    )
    return {
        "status": "completed",
        "final_answer": str(results[-1].output),
    }


def route_after_planning(state: WorkflowState) -> str:
    if state.get("plan") and not state.get("errors"):
        return "execute"
    return "verify"


def route_after_verification(state: WorkflowState) -> str:
    if (
        state.get("status") == "running"
        and state.get("current_step", 0) < len(state.get("plan", []))
    ):
        return "execute"
    return "end"


def build_workflow(checkpointer=None):
    graph = StateGraph(WorkflowState)

    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("verifier", verifier_node)

    graph.add_edge(START, "planner")

    graph.add_conditional_edges(
        "planner",
        route_after_planning,
        {
            "execute": "executor",
            "verify": "verifier",
        },
    )

    graph.add_conditional_edges(
        "executor",
        route_after_execution,
        {
            "retry": "executor",
            "verify": "verifier",
        },
    )

    graph.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "execute": "executor",
            "end": END,
        },
    )

    return graph.compile(checkpointer=checkpointer)


def run_workflow(
    task: str,
    max_steps: int = 5,
    session_id: str | None = None,
    checkpointer=None,
) -> WorkflowState:
    """Run a workflow with a persistent Redis checkpoint by default."""

    session_id = session_id or str(uuid4())

    logger.info(
        "Workflow engine started | session_id=%s | max_steps=%s",
        session_id,
        max_steps,
    )

    initial_state: WorkflowState = {
        "task": task,
        "session_id": session_id,
        "max_steps": max_steps,
        "plan": [],
        "current_step": 0,
        "tool_results": [],
        "errors": [],
        "status": "pending",
        "final_answer": "",
        "max_retries": 2,
        "retry_count": 0,
        "retry_pending": False,
        "last_error": "",
    }

    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    try:
        # Allow tests or other callers to inject their own checkpointer.
        if checkpointer is not None:
            graph = build_workflow(checkpointer=checkpointer)
            result = graph.invoke(initial_state, config=config)
        else:
            # Production runs use Redis for persistent checkpoints.
            with RedisSaver.from_conn_string(
                get_settings().redis_url
            ) as redis_saver:
                redis_saver.setup()
                graph = build_workflow(checkpointer=redis_saver)
                result = graph.invoke(initial_state, config=config)

        logger.info(
            "Workflow engine finished | session_id=%s | status=%s",
            session_id,
            result.get("status", "unknown"),
        )
        return result

    except Exception:
        logger.exception(
            "Workflow engine raised an exception | session_id=%s",
            session_id,
        )
        raise
