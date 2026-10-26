"""Agent graph helpers."""

from app.agents.graph import collect_tool_events, infer_return_id


def test_infer_return_id_from_message() -> None:
    assert infer_return_id("Please check R108 for repair", None) == "R108"
    assert infer_return_id("hello", None) is None
    assert infer_return_id("hello", "R101") == "R101"


def test_collect_tool_events_pairs_results() -> None:
    from langchain_core.messages import AIMessage, ToolMessage

    messages = [
        AIMessage(
            content="",
            tool_calls=[{"id": "c1", "name": "get_return_details", "args": {"return_id": "R102"}}],
        ),
        ToolMessage(content='{"return_id":"R102"}', tool_call_id="c1", name="get_return_details"),
        AIMessage(content="Done."),
    ]
    events = collect_tool_events(messages)
    assert len(events) == 1
    assert events[0]["tool"] == "get_return_details"
    assert events[0]["result_preview"]
