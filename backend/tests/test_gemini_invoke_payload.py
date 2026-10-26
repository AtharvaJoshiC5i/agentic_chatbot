"""Ensure Gemini invoke path serializes thought signatures on replay."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.llm.gemini_openai_compat import GeminiChatOpenAI, attach_tool_call_extras
from app.llm.gemini import get_gemini_chat_model


@tool
def get_return_details(return_id: str) -> str:
    """Return details."""
    return "ok"


def test_guarded_invoke_replays_thought_signature(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()

    payloads: list[dict] = []
    orig = GeminiChatOpenAI._get_request_payload

    def capture(self, input_, **kwargs):
        payload = orig(self, input_, **kwargs)
        payloads.append(payload)
        return payload

    monkeypatch.setattr(GeminiChatOpenAI, "_get_request_payload", capture)

    model = get_gemini_chat_model().bind_tools([get_return_details])
    gemini = model._unwrap_gemini_chat_model()
    assert gemini is not None

    fake = MagicMock()
    fake.model_dump.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "get_return_details",
                                "arguments": '{"return_id":"R105"}',
                            },
                            "extra_content": {"google": {"thought_signature": "SIG1"}},
                        }
                    ],
                }
            }
        ]
    }
    gemini.client = MagicMock()
    gemini.client.create = MagicMock(return_value=fake)

    first = model.invoke([HumanMessage(content="Details for R105")])
    assert isinstance(first, AIMessage)
    assert first.tool_calls

    second_fake = MagicMock()
    second_fake.model_dump.return_value = {
        "choices": [{"message": {"role": "assistant", "content": "done"}}]
    }
    gemini.client.create = MagicMock(return_value=second_fake)

    model.invoke(
        [
            HumanMessage(content="Details for R105"),
            first,
            ToolMessage(content='{"return_id":"R105"}', tool_call_id="c1"),
        ]
    )

    assert len(payloads) >= 2
    replay = payloads[-1]["messages"]
    assistant_rows = [m for m in replay if m.get("role") == "assistant" and m.get("tool_calls")]
    assert assistant_rows, replay
    sig = assistant_rows[0]["tool_calls"][0]["extra_content"]["google"]["thought_signature"]
    assert sig == "SIG1"
