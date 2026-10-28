
from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


def test_create_workflow_returns_result(monkeypatch):
    def fake_run_workflow(task, max_steps, session_id=None):
        return {
            "session_id": session_id or "generated-session",
            "status": "completed",
            "final_answer": "42",
            "current_step": 1,
            "errors": [],
        }

    monkeypatch.setattr(main, "run_workflow", fake_run_workflow)

    response = client.post(
        "/workflows",
        json={"task": "Add 15 and 27"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["answer"] == "42"
    assert response.json()["steps_executed"] == 1


def test_create_workflow_preserves_session_id(monkeypatch):
    def fake_run_workflow(task, max_steps, session_id=None):
        return {
            "session_id": session_id or "generated-session",
            "status": "completed",
            "final_answer": "42",
            "current_step": 1,
            "errors": [],
        }

    monkeypatch.setattr(main, "run_workflow", fake_run_workflow)

    response = client.post(
        "/workflows",
        json={
            "task": "Add 15 and 27",
            "session_id": "my-test-session",
        },
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "my-test-session"


def test_create_workflow_rejects_too_many_steps():
    response = client.post(
        "/workflows",
        json={"task": "Add 15 and 27", "max_steps": 11},
    )

    assert response.status_code == 422
