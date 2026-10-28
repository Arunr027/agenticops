
from app.session_service import get_session_history, get_session_state
import logging
import time

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.models import WorkflowRequest, WorkflowResponse
from app.workflow import run_workflow

settings = get_settings()

# Configure application logging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("agenticops.api")

app = FastAPI(
    title=settings.app_name,
    description="A stateful multi-agent workflow engine.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    logger.info("Health check requested")

    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    return {
        "message": "Welcome to AgenticOps",
        "docs": "/docs",
        "health": "/health",
    }


@app.post(
    "/workflows",
    response_model=WorkflowResponse,
    tags=["Workflows"],
)
def create_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """Plan, execute, and verify a task using the workflow engine."""

    start_time = time.perf_counter()
    session_id = request.session_id or "auto-generated"

    logger.info(
        "Workflow request received | session_id=%s | max_steps=%s",
        session_id,
        request.max_steps,
    )

    try:
        state = run_workflow(
            task=request.task,
            max_steps=request.max_steps,
            session_id=request.session_id,
        )

        duration_seconds = time.perf_counter() - start_time
        status = state.get("status", "failed")

        logger.info(
            "Workflow finished | session_id=%s | status=%s "
            "| steps_executed=%s | duration_seconds=%.3f",
            state.get("session_id", session_id),
            status,
            state.get("current_step", 0),
            duration_seconds,
        )

    except Exception:
        duration_seconds = time.perf_counter() - start_time

        logger.exception(
            "Workflow execution raised an exception | session_id=%s "
            "| duration_seconds=%.3f",
            session_id,
            duration_seconds,
        )

        # Avoid exposing internal errors or configuration secrets to clients.
        raise HTTPException(
            status_code=503,
            detail="Workflow execution failed. Check application logs.",
        ) from None

    return WorkflowResponse(
        session_id=state["session_id"],
        status=state.get("status", "failed"),
        answer=state.get("final_answer", ""),
        steps_executed=state.get("current_step", 0),
        errors=state.get("errors", []),
    )

@app.get("/workflows/{session_id}", tags=["Workflows"])
def read_workflow_session(session_id: str) -> dict:
    """Retrieve the latest saved state for a workflow session."""

    state = get_session_state(session_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow session not found.",
        )

    return {
        "session_id": session_id,
        "task": state.get("task", ""),
        "status": state.get("status", "unknown"),
        "steps_executed": state.get("current_step", 0),
        "answer": state.get("final_answer", ""),
        "errors": state.get("errors", []),
    }


@app.get(
    "/workflows/{session_id}/history",
    tags=["Workflows"],
)
def read_workflow_history(session_id: str) -> dict:
    """Retrieve checkpoint history for a workflow session."""

    state = get_session_state(session_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow session not found.",
        )

    history = get_session_history(session_id)

    return {
        "session_id": session_id,
        "checkpoint_count": len(history),
        "history": history,
    }
