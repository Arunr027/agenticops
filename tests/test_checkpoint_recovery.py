
from langgraph.checkpoint.redis import RedisSaver

from app.config import get_settings
from app.workflow import build_workflow


def test_saved_workflow_checkpoint_can_be_recovered():
    session_id = "swagger-demo-001"
    config = {"configurable": {"thread_id": session_id}}

    with RedisSaver.from_conn_string(get_settings().redis_url) as saver:
        saver.setup()
        workflow = build_workflow(checkpointer=saver)

        saved_state = workflow.get_state(config)

    assert saved_state.values, "No checkpoint state was recovered"
    assert saved_state.values.get("session_id") == session_id
    assert saved_state.values.get("final_answer") == "42"
    assert saved_state.values.get("status") == "completed"
