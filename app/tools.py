
import math
import multiprocessing
import queue
import time
from typing import Any, Callable

from app.config import get_settings
from app.models import ToolResult


def _elapsed_ms(start_time: float) -> float:
    """Return elapsed execution time in milliseconds."""
    return round((time.perf_counter() - start_time) * 1000, 2)


def _validate_number(value: Any, name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")

    return value


def add_numbers(a: Any, b: Any) -> int | float:
    """Add two finite numbers."""
    a = _validate_number(a, "a")
    b = _validate_number(b, "b")
    return a + b


def multiply_numbers(a: Any, b: Any) -> int | float:
    """Multiply two finite numbers."""
    a = _validate_number(a, "a")
    b = _validate_number(b, "b")
    return a * b


def get_text_length(text: Any) -> int:
    """Return the number of characters in a string."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")

    return len(text)


TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "add_numbers": add_numbers,
    "multiply_numbers": multiply_numbers,
    "get_text_length": get_text_length,
}


def _run_tool_in_process(
    result_queue: multiprocessing.Queue,
    tool: Callable[..., Any],
    arguments: dict[str, Any],
) -> None:
    """Run an importable tool in a child process."""
    try:
        result_queue.put(("success", tool(**arguments), None))

    except (TypeError, ValueError) as exc:
        result_queue.put(("error", str(exc), "permanent"))

    except Exception as exc:
        result_queue.put(
            ("error", f"{type(exc).__name__}: {exc}", "permanent")
        )


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    step_id: int = 1,
) -> ToolResult:
    """Execute a registered tool with a hard timeout and timing."""
    start_time = time.perf_counter()

    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return ToolResult(
            step_id=step_id,
            tool_name=tool_name,
            success=False,
            error=f"Unknown tool: {tool_name}",
            error_type="permanent",
            duration_ms=_elapsed_ms(start_time),
        )

    timeout = get_settings().tool_timeout_seconds

    if timeout <= 0:
        return ToolResult(
            step_id=step_id,
            tool_name=tool_name,
            success=False,
            error="Tool timeout must be greater than zero.",
            error_type="permanent",
            duration_ms=_elapsed_ms(start_time),
        )

    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(
        target=_run_tool_in_process,
        args=(result_queue, tool, arguments),
    )

    try:
        process.start()
        process.join(timeout)

        if process.is_alive():
            process.terminate()
            process.join(timeout=1)

            if process.is_alive():
                process.kill()
                process.join(timeout=1)

            return ToolResult(
                step_id=step_id,
                tool_name=tool_name,
                success=False,
                error=f"Tool timed out after {timeout} seconds.",
                error_type="temporary",
                duration_ms=_elapsed_ms(start_time),
            )

        try:
            kind, value, error_type = result_queue.get(timeout=1)

        except queue.Empty:
            return ToolResult(
                step_id=step_id,
                tool_name=tool_name,
                success=False,
                error="Tool process exited without returning a result.",
                error_type="permanent",
                duration_ms=_elapsed_ms(start_time),
            )

        if kind == "success":
            return ToolResult(
                step_id=step_id,
                tool_name=tool_name,
                success=True,
                output=value,
                duration_ms=_elapsed_ms(start_time),
            )

        return ToolResult(
            step_id=step_id,
            tool_name=tool_name,
            success=False,
            error=value,
            error_type=error_type,
            duration_ms=_elapsed_ms(start_time),
        )

    except Exception as exc:
        if process.pid is not None and process.is_alive():
            process.terminate()
            process.join(timeout=1)

            if process.is_alive():
                process.kill()
                process.join(timeout=1)

        return ToolResult(
            step_id=step_id,
            tool_name=tool_name,
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            error_type="permanent",
            duration_ms=_elapsed_ms(start_time),
        )

    finally:
        result_queue.close()
        result_queue.join_thread()
