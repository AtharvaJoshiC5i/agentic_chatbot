"""Trim chat history before sending to the LLM."""

from functools import lru_cache

from app.agents.limits import MAX_HISTORY_TURNS, MAX_TURN_CHARS
from app.config import get_settings
from app.llm.context_window import estimate_tokens, truncate_text_to_tokens


@lru_cache
def _history_token_budget() -> int:
    return max(512, get_settings().llm_history_max_tokens)


def _trim_turn_content(content: str) -> str:
    text = (content or "").strip()
    if len(text) <= MAX_TURN_CHARS:
        return text
    return text[: MAX_TURN_CHARS - 3] + "..."


def trim_history(conversation_history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """
    Keep recent turns within count and token budgets.

    Newest turns win; older turns drop first when over MAX_HISTORY_TOKEN_BUDGET.
    """
    if not conversation_history:
        return []

    recent = conversation_history[-MAX_HISTORY_TURNS:]
    selected: list[dict[str, str]] = []
    tokens_used = 0

    for turn in reversed(recent):
        role = turn.get("role", "user")
        content = _trim_turn_content(turn.get("content") or "")
        if not content:
            continue
        turn_tokens = estimate_tokens(content) + 4
        if selected and tokens_used + turn_tokens > _history_token_budget():
            break
        selected.append({"role": role, "content": content})
        tokens_used += turn_tokens

    selected.reverse()

    # If a single huge turn remains over budget, hard-truncate it.
    budget = _history_token_budget()
    if len(selected) == 1 and tokens_used > budget:
        only = selected[0]
        only["content"] = truncate_text_to_tokens(only["content"], budget)

    return selected
