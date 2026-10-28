
import inspect

from google import genai
from google.genai import types

from app.config import get_settings
from app.models import WorkflowPlan
from app.tools import TOOL_REGISTRY


def generate_plan(task: str, max_steps: int = 5) -> WorkflowPlan:
    """Ask Gemini for a plan, then validate it before execution."""

    settings = get_settings()

    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Please configure your Gemini API key."
        )

    client = genai.Client(api_key=settings.gemini_api_key)

    available_tools = {
        "add_numbers": "Add two numbers: a, b",
        "multiply_numbers": "Multiply two numbers: a, b",
        "get_text_length": "Count characters in a string: text",
    }

    prompt = f"""
You are the planning agent in AgenticOps.

Convert the user's task into a JSON workflow plan.

Available tools:
{available_tools}

Rules:
- Use only the listed tools.
- Never invent tool names or arguments.
- Each step must contain step_id, description, tool_name and arguments.
- Use sequential step IDs starting at 1.
- Keep the plan within {max_steps} steps.
- If the task cannot be completed using the available tools,
  return an empty steps list and explain why in the goal.
- Do not execute tools yourself.

User task:
{task}
"""

    # Request a plan from Gemini with clear error reporting.
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )

    except Exception as exc:
        error_message = str(exc)
        error_lower = error_message.lower()

        if (
            "resource_exhausted" in error_lower
            or "quota" in error_lower
            or "429" in error_message
        ):
            raise RuntimeError(
                f"Gemini quota exhausted for model "
                f"'{settings.gemini_model}'. "
                "Check your Gemini API quota and billing settings. "
                "Retry after quota becomes available."
            ) from exc

        raise RuntimeError(
            f"Gemini planning request failed: {error_message}"
        ) from exc

    # Parse and validate Gemini's response.
    parsed = getattr(response, "parsed", None)

    if isinstance(parsed, WorkflowPlan):
        plan = parsed

    elif isinstance(parsed, dict):
        plan = WorkflowPlan.model_validate(parsed)

    else:
        response_text = getattr(response, "text", None)

        if not isinstance(response_text, str) or not response_text.strip():
            raise ValueError(
                "Gemini returned an empty planning response."
            )

        plan = WorkflowPlan.model_validate_json(response_text)

    # Enforce the workflow step limit.
    if len(plan.steps) > max_steps:
        raise ValueError(
            f"Plan exceeds the maximum of {max_steps} steps."
        )

    # Validate every step and its tool arguments before execution.
    for index, step in enumerate(plan.steps, start=1):

        if step.step_id != index:
            raise ValueError(
                "Plan step IDs must be sequential, starting at 1."
            )

        tool = TOOL_REGISTRY.get(step.tool_name)

        if tool is None:
            raise ValueError(
                f"Gemini selected an unregistered tool: "
                f"{step.tool_name}"
            )

        try:
            inspect.signature(tool).bind(**step.arguments)

        except TypeError as exc:
            raise ValueError(
                f"Invalid arguments for {step.tool_name}: {exc}"
            ) from exc

    return plan
