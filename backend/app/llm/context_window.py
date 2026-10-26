"""Context-window budgeting for LangChain messages sent to chat models."""

from __future__ import annotations

import json
from copy import copy
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.config import Settings, get_settings

# Rough OpenAI-style token estimate (~4 chars/token for Latin text).
_CHARS_PER_TOKEN = 4
_MESSAGE_OVERHEAD_TOKENS = 8

_TRUNCATION_FOOTER = "\n…[truncated to fit context window]"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or block))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content or "")


def estimate_message_tokens(message: BaseMessage) -> int:
    tokens = _MESSAGE_OVERHEAD_TOKENS + estimate_tokens(_message_text(message))
    if isinstance(message, AIMessage) and message.tool_calls:
        tokens += estimate_tokens(json.dumps(message.tool_calls, default=str))
    return tokens


def truncate_text_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    keep = max(0, max_chars - len(_TRUNCATION_FOOTER))
    return text[:keep] + _TRUNCATION_FOOTER


def input_token_budget(provider_id: str, settings: Settings | None = None) -> int:
    """Tokens available for a single model call (input), after output reserve."""
    settings = settings or get_settings()
    reserve = max(512, settings.llm_context_output_reserve)
    cap = max(2048, settings.llm_context_input_tokens)
    return max(1024, cap - reserve)


def per_tool_message_token_cap(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    return max(64, settings.llm_tool_message_max_tokens)


def _shrink_tool_message(message: ToolMessage, max_tokens: int) -> ToolMessage:
    text = _message_text(message)
    if estimate_tokens(text) <= max_tokens:
        return message
    shrunk = copy(message)
    shrunk.content = truncate_text_to_tokens(text, max_tokens)
    return shrunk


def _split_system_prefix(messages: list[BaseMessage]) -> tuple[list[BaseMessage], list[BaseMessage]]:
    idx = 0
    while idx < len(messages) and isinstance(messages[idx], SystemMessage):
        idx += 1
    return messages[:idx], messages[idx:]


def _drop_leading_round(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Drop the oldest non-system message(s), keeping tool-call groups consistent."""
    if not messages:
        return messages
    drop = messages[0]
    rest = messages[1:]
    if isinstance(drop, AIMessage) and drop.tool_calls:
        pending = {call.get("id") for call in drop.tool_calls if call.get("id")}
        while pending and rest and isinstance(rest[0], ToolMessage):
            tm = rest[0]
            if tm.tool_call_id in pending:
                pending.discard(tm.tool_call_id)
                rest = rest[1:]
            else:
                break
    return rest


def _protected_tail(body: list[BaseMessage]) -> int:
    """Index in body where the protected suffix starts (latest user turn + after)."""
    for i in range(len(body) - 1, -1, -1):
        if isinstance(body[i], HumanMessage):
            return i
    return max(0, len(body) - 1)


def fit_messages_to_context_budget(
    messages: list[BaseMessage],
    *,
    provider_id: str,
    max_input_tokens: int | None = None,
    settings: Settings | None = None,
) -> list[BaseMessage]:
    """
    Fit messages into the model context without breaking tool-call pairing.

    Strategy (in order):
    1. Keep all leading system messages.
    2. Truncate oldest tool outputs first.
    3. Drop oldest conversation/tool rounds before the latest user message.
    4. Aggressively truncate remaining tool outputs.
    """
    if not messages:
        return messages

    settings = settings or get_settings()
    budget = max_input_tokens if max_input_tokens is not None else input_token_budget(provider_id, settings)
    tool_cap = per_tool_message_token_cap(settings)

    working = list(messages)

    def total_tokens() -> int:
        return sum(estimate_message_tokens(m) for m in working)

    if total_tokens() <= budget:
        return working

    prefix, body = _split_system_prefix(working)
    prefix_tokens = sum(estimate_message_tokens(m) for m in prefix)
    body_budget = max(512, budget - prefix_tokens)

    # Pass 1 — shrink tool payloads from oldest to newest.
    for i in range(len(body)):
        if isinstance(body[i], ToolMessage):
            body[i] = _shrink_tool_message(body[i], tool_cap)
        if sum(estimate_message_tokens(m) for m in prefix + body) <= budget:
            return prefix + body

    # Pass 2 — drop oldest rounds before the latest human turn.
    tail_start = _protected_tail(body)
    droppable = body[:tail_start]
    protected = body[tail_start:]
    while droppable and sum(estimate_message_tokens(m) for m in prefix + droppable + protected) > budget:
        droppable = _drop_leading_round(droppable)
    body = droppable + protected
    working = prefix + body
    if total_tokens() <= budget:
        return working

    # Pass 3 — shrink all tool messages to a minimal cap.
    minimal_tool_cap = max(48, tool_cap // 2)
    for i in range(len(body)):
        if isinstance(body[i], ToolMessage):
            body[i] = _shrink_tool_message(body[i], minimal_tool_cap)
    working = prefix + body
    if total_tokens() <= budget:
        return working

    # Pass 4 — drop more droppable rounds if still over budget.
    tail_start = _protected_tail(body)
    droppable = body[:tail_start]
    protected = body[tail_start:]
    while droppable and sum(estimate_message_tokens(m) for m in prefix + droppable + protected) > body_budget:
        droppable = _drop_leading_round(droppable)
    body = droppable + protected
    return prefix + body
