
import re
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.models import PlanStep
from app.state import WorkflowState
from app.tools import execute_tool


def _parse_number(value: str) -> int | float:
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def planner_node(state: WorkflowState) -> dict[str, Any]:
    """Create a deterministic plan for supported demo tasks."""
    task = state.get("task", "").strip()
    max_steps = state.get("max_steps", 5)
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

    if not plan:
        return {
            "plan": [],
            "current_step": 0,
            "tool_results": [],
            "errors": [
                "The deterministic planner cannot handle this task yet."
            ],
            "status": "failed",
            "final_answer": "",
        }

    if len(plan) > max_steps:
        return {
            "plan": [],
            "current_step": 0,
            "tool_results": [],
            "errors": ["The plan exceeds the configured step limit."],
            "status": "failed",
            "final_answer": "",
        }

    return {
        "plan": plan,
        "current_step": 0,
        "tool_results": [],
        "errors": [],
        "status": "running",
        "final_answer": "",
    }


def executor_node(state: WorkflowState) -> dict[str, Any]:
    """Execute the next planned step using the registered tools."""
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)

    if current_step >= len(plan):
        return {
            "errors": state.get("errors", [])
            + ["No planned step is available to execute."],
            "status": "failed",
        }

    step = plan[current_step]
    result = execute_tool(
        tool_name=step.tool_name,
        arguments=step.arguments,
        step_id=step.step_id,
    )

    results = state.get("tool_results", []) + [result]
    errors = list(state.get("errors", []))

    if not result.success:
        errors.append(result.error or "Tool execution failed.")

    return {
        "tool_results": results,
        "current_step": current_step + 1,
        "errors": errors,
        "status": "running" if result.success else "failed",
    }


def verifier_node(state: WorkflowState) -> dict[str, Any]:
    """Check tool results and determine the workflow outcome."""
    errors = state.get("errors", [])
    results = state.get("tool_results", [])
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)

    if errors:
        return {
            "status": "failed",
            "final_answer": "Workflow failed: " + "; ".join(errors),
        }

    if not results or not results[-1].success:
        return {
            "status": "failed",
            "final_answer": "Workflow failed: no successful tool result.",
            "errors": ["No successful tool result was available."],
        }

    if current_step < len(plan):
        return {"status": "running"}

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


def build_workflow():
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

    graph.add_edge("executor", "verifier")

    graph.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "execute": "executor",
            "end": END,
        },
    )

    return graph.compile()


def run_workflow(task: str, max_steps: int = 5) -> WorkflowState:
    """Run one workflow and return its final state."""
    graph = build_workflow()

    initial_state: WorkflowState = {
        "task": task,
        "session_id": "local-session",
        "max_steps": max_steps,
        "plan": [],
        "current_step": 0,
        "tool_results": [],
        "errors": [],
        "status": "pending",
        "final_answer": "",
    }

    return graph.invoke(initial_state)
