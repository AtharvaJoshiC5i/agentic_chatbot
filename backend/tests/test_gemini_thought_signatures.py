"""Gemini OpenAI-compat tool calls must round-trip thought signatures."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.llm.gemini_openai_compat import (
    OPENAI_TOOL_CALL_EXTRAS_KEY,
    attach_tool_call_extras,
    gemini_convert_message_to_dict,
    propagate_thought_signatures,
)


def test_propagate_thought_signature_to_parallel_tool_calls() -> None:
    raw = [
        {
            "id": "call_a",
            "type": "function",
            "function": {"name": "get_return_details", "arguments": "{}"},
            "extra_content": {"google": {"thought_signature": "sig-parallel"}},
        },
        {
            "id": "call_b",
            "type": "function",
            "function": {"name": "get_inspection_results", "arguments": "{}"},
        },
    ]
    out = propagate_thought_signatures(raw)
    assert out[1]["extra_content"]["google"]["thought_signature"] == "sig-parallel"


def test_tool_call_thought_signature_round_trip() -> None:
    raw_tool_calls = [
        {
            "id": "call_abc",
            "type": "function",
            "function": {
                "name": "get_return_details",
                "arguments": '{"return_id":"R101"}',
            },
            "extra_content": {
                "google": {"thought_signature": "sig-test-123"},
            },
        }
    ]
    assistant = AIMessage(content="", tool_calls=[])
    attach_tool_call_extras(assistant, raw_tool_calls)
    assistant.tool_calls = [
        {
            "id": "call_abc",
            "name": "get_return_details",
            "args": {"return_id": "R101"},
        }
    ]

    outbound = gemini_convert_message_to_dict(assistant)
    assert outbound["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "sig-test-123"

    history = [
        HumanMessage(content="Details for R101"),
        assistant,
        ToolMessage(content='{"return_id":"R101"}', tool_call_id="call_abc"),
    ]
    for message in history:
        if isinstance(message, AIMessage):
            payload = gemini_convert_message_to_dict(message)
            assert payload["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "sig-test-123"
            assert OPENAI_TOOL_CALL_EXTRAS_KEY in message.additional_kwargs
