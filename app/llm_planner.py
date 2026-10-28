
import inspect

from google import genai
from google.genai import types

from app.config import get_settings
from app.models import PlanStep, WorkflowPlan
from app.tools import TOOL_REGISTRY


def generate_plan(task: str, max_steps: int = 5) -> WorkflowPlan:
    """Ask Gemini for a plan, then validate it before execution."""

    settings = get_settings()

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

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

    
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )

    
    parsed = getattr(response, "parsed", None)

    if isinstance(parsed, WorkflowPlan):
        plan = parsed
    elif isinstance(parsed, dict):
        plan = WorkflowPlan.model_validate(parsed)
    else:
        text = getattr(response, "text", None)

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Gemini returned an empty planning response.")

        # Validate Gemini's JSON locally with Pydantic.
        plan = WorkflowPlan.model_validate_json(text)

    if len(plan.steps) > max_steps:
        raise ValueError(
            f"Plan exceeds the maximum of {max_steps} steps."
        )

    for index, step in enumerate(plan.steps, start=1):
        if step.step_id != index:
            raise ValueError("Plan step IDs must be sequential, starting at 1.")

        tool = TOOL_REGISTRY.get(step.tool_name)
        if tool is None:
            raise ValueError(
                f"Gemini selected an unregistered tool: {step.tool_name}"
            )

        try:
            inspect.signature(tool).bind(**step.arguments)
        except TypeError as exc:
            raise ValueError(
                f"Invalid arguments for {step.tool_name}: {exc}"
            ) from exc

    return plan
