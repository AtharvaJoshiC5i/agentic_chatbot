"""Context window trimming for agent + LLM calls."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.llm.context_window import (
    estimate_tokens,
    fit_messages_to_context_budget,
    truncate_text_to_tokens,
)
from app.agents.history import trim_history


def test_truncate_text_to_tokens_adds_footer() -> None:
    text = "x" * 400
    out = truncate_text_to_tokens(text, 10)
    assert "truncated" in out
    assert len(out) < len(text)


def test_fit_messages_keeps_system_and_latest_human() -> None:
    system = SystemMessage(content="You are the returns agent.")
    old_human = HumanMessage(content="old question " * 200)
    old_ai = AIMessage(content="old answer " * 200)
    tool = ToolMessage(content="tool payload " * 500, tool_call_id="t1", name="get_return_details")
    latest = HumanMessage(content="What is R102 status?")

    messages = [system, old_human, old_ai, tool, latest]
    fitted = fit_messages_to_context_budget(messages, provider_id="groq", max_input_tokens=400)
    assert isinstance(fitted[0], SystemMessage)
    assert fitted[-1].content == latest.content
    total = sum(estimate_tokens(str(m.content)) for m in fitted)
    assert total < 2000


def test_trim_history_respects_token_budget() -> None:
    history = [
        {"role": "user", "content": "u" * 5000},
        {"role": "assistant", "content": "a" * 5000},
        {"role": "user", "content": "recent question"},
    ]
    trimmed = trim_history(history)
    assert trimmed[-1]["content"] == "recent question"
    assert len(trimmed) <= 3
