"""Agent step trace builder."""

from langchain_core.messages import AIMessage, ToolMessage

from app.agents.steps import build_agent_steps


def test_build_agent_steps_tool_flow() -> None:
    workflow = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "c1",
                    "name": "run_return_investigation",
                    "args": {"return_id": "R102"},
                }
            ],
        ),
        ToolMessage(content='{"return_id":"R102"}', tool_call_id="c1", name="run_return_investigation"),
    ]
    steps = build_agent_steps(workflow, include_synthesis=True)
    kinds = [s["kind"] for s in steps]
    assert kinds[0] == "status"
    assert "plan" in kinds
    tool_steps = [s for s in steps if s["kind"] == "tool"]
    assert len(tool_steps) == 1
    assert tool_steps[0]["status"] == "completed"
    assert tool_steps[0]["output"]
    assert steps[-1]["kind"] == "synthesis"
