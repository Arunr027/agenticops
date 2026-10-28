
from typing import Any

from langgraph.checkpoint.redis import RedisSaver

from app.config import get_settings


def _get_checkpoint_config(session_id: str) -> dict[str, Any]:
    """Build the LangGraph configuration for a session."""

    return {
        "configurable": {
            "thread_id": session_id,
        }
    }
def _serialize_tool_result(result: Any) -> dict[str, Any]:
    """Convert a tool result into a clean dictionary."""

    if hasattr(result, "model_dump"):
        return result.model_dump()

    if isinstance(result, dict) and isinstance(result.get("kwargs"), dict):
        return result["kwargs"]

    if isinstance(result, dict):
        return result

    return {"value": str(result)}


def _summarize_checkpoint(checkpoint: Any) -> dict[str, Any]:
    """Return useful workflow details from a saved checkpoint."""

    values = checkpoint.checkpoint.get("channel_values", {})
    metadata = checkpoint.metadata or {}

    tool_results = values.get("tool_results", [])
    plan = values.get("plan", [])

    return {
        "checkpoint_id": checkpoint.config.get(
            "configurable", {}
        ).get("checkpoint_id"),
        "step": metadata.get("step"),
        "source": metadata.get("source"),
        "task": values.get("task", ""),
        "status": values.get("status", "unknown"),
        "current_step": values.get("current_step", 0),
        "planned_steps": len(plan),
        "tool_results": [
    _serialize_tool_result(result)
    for result in tool_results
],
        "errors": values.get("errors", []),
        "final_answer": values.get("final_answer", ""),
    }


def get_session_state(session_id: str) -> dict[str, Any] | None:
    """Return the latest saved workflow state for a session."""

    config = _get_checkpoint_config(session_id)

    with RedisSaver.from_conn_string(
        get_settings().redis_url
    ) as redis_saver:
        redis_saver.setup()
        checkpoint = redis_saver.get_tuple(config)

        if checkpoint is None:
            return None

        return checkpoint.checkpoint.get("channel_values", {})


def get_session_history(session_id: str) -> list[dict[str, Any]]:
    """Return workflow details from checkpoints, newest first."""

    config = _get_checkpoint_config(session_id)
    history: list[dict[str, Any]] = []

    with RedisSaver.from_conn_string(
        get_settings().redis_url
    ) as redis_saver:
        redis_saver.setup()

        for checkpoint in redis_saver.list(config):
            history.append(_summarize_checkpoint(checkpoint))

    return history
