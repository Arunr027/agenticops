
from fastapi.testclient import TestClient

from app.main import app
from app.session_service import get_session_history, get_session_state

client = TestClient(app)


def test_get_workflow_session_success(monkeypatch):
    """An existing session should return its saved state."""

    monkeypatch.setattr(
        "app.main.get_session_state",
        lambda session_id: {
            "task": "Add 15 and 27",
            "status": "completed",
            "current_step": 1,
            "final_answer": "42",
            "errors": [],
        },
    )

    response = client.get("/workflows/test-session-123")

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "test-session-123",
        "task": "Add 15 and 27",
        "status": "completed",
        "steps_executed": 1,
        "answer": "42",
        "errors": [],
    }


def test_get_workflow_session_not_found(monkeypatch):
    """An unknown session should return 404."""

    monkeypatch.setattr(
        "app.main.get_session_state",
        lambda session_id: None,
    )

    response = client.get("/workflows/missing-session")

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow session not found."


def test_get_workflow_history_success(monkeypatch):
    """An existing session should return its checkpoint history."""

    monkeypatch.setattr(
        "app.main.get_session_state",
        lambda session_id: {"task": "Add 15 and 27", "status": "completed"},
    )

    fake_history = [
        {"checkpoint_id": "checkpoint-2", "step": 1, "source": "loop"},
        {"checkpoint_id": "checkpoint-1", "step": 0, "source": "loop"},
    ]

    monkeypatch.setattr(
        "app.main.get_session_history",
        lambda session_id: fake_history,
    )

    response = client.get("/workflows/test-session-123/history")

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "test-session-123",
        "checkpoint_count": 2,
        "history": fake_history,
    }


def test_get_workflow_history_not_found(monkeypatch):
    """An unknown session should return 404 for history too."""

    monkeypatch.setattr(
        "app.main.get_session_state",
        lambda session_id: None,
    )

    response = client.get("/workflows/missing-session/history")

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow session not found."
