"""LangGraph ReAct agent with Groq or Gemini + tools."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from app.agents.context import agent_run_config, apply_agent_context_if_provided
from app.llm.context_window import fit_messages_to_context_budget
from app.agents.document_citations import enrich_tool_events_with_documents
from app.agents.visuals import build_visuals
from app.agents.evidence import build_supporting_evidence
from app.agents.history import trim_history
from app.agents.operator_response import format_operator_response
from app.agents.prompts import build_system_prompt
from app.services.return_workflow import build_agent_workflow_context_message
from app.models.enums import UserRole
from app.agents.steps import build_agent_steps, diff_steps
from app.llm.router import get_chat_model, normalize_provider
from app.agents.tool_access import filter_tools_for_role
from app.tools.action_tools import ACTION_TOOLS
from app.tools.recovery_tools import get_recovery_options, get_recovery_recommendation
from app.tools.doc_tools import DOCUMENT_TOOLS
from app.tools.investigation_tools import run_return_investigation
from app.tools.portfolio_tools import PORTFOLIO_TOOLS
from app.tools.sql_tools import SQL_TOOLS
from app.tools.workflow_tools import WORKFLOW_TOOLS

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.security.deps import CurrentUser

RETURN_ID_RE = re.compile(r"\bR\d{3}\b", re.IGNORECASE)

ALL_TOOLS = (
    SQL_TOOLS
    + DOCUMENT_TOOLS
    + [run_return_investigation]
    + WORKFLOW_TOOLS
    + PORTFOLIO_TOOLS
    + ACTION_TOOLS
    + [get_recovery_options, get_recovery_recommendation]
)


def infer_return_id(message: str, explicit: str | None) -> str | None:
    if explicit and explicit.strip():
        return explicit.strip().upper()
    match = RETURN_ID_RE.search(message)
    return match.group(0).upper() if match else None


def _preview_tool_content(content: Any, max_chars: int = 900) -> str:
    text = content if isinstance(content, str) else str(content)
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def collect_tool_events(messages: list) -> list[dict[str, Any]]:
    """Pair tool calls with result previews for the UI."""
    events: list[dict[str, Any]] = []
    pending_by_id: dict[str, int] = {}

    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                call_id = call.get("id") or f"{call.get('name')}-{len(events)}"
                events.append(
                    {
                        "tool": call.get("name"),
                        "args": call.get("args") or {},
                        "tool_call_id": call_id,
                    }
                )
                pending_by_id[call_id] = len(events) - 1

        if isinstance(message, ToolMessage):
            preview = _preview_tool_content(message.content)
            call_id = message.tool_call_id
            idx = pending_by_id.get(call_id) if call_id else None
            if idx is not None and "result_preview" not in events[idx]:
                events[idx]["result_preview"] = preview
            else:
                events.append(
                    {
                        "tool": message.name or "tool",
                        "args": {},
                        "result_preview": preview,
                    }
                )

    for ev in events:
        ev.pop("tool_call_id", None)
    return events


def build_initial_messages(
    user_message: str,
    *,
    return_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    user: CurrentUser | None = None,
    db: Session | None = None,
) -> tuple[list, str | None]:
    focus_return = infer_return_id(user_message, return_id)
    messages: list = [SystemMessage(content=build_system_prompt(user))]
    if focus_return and db is not None:
        ctx = build_agent_workflow_context_message(db, focus_return)
        if ctx:
            messages.append(SystemMessage(content=ctx))
    if focus_return:
        if user is not None and user.role == UserRole.WAREHOUSE_MANAGER:
            messages.append(
                SystemMessage(
                    content=(
                        f"Active return_id={focus_return}. "
                        "Call get_warehouse_handoff_status_tool first, then get_inspection_results. "
                        "Do not call run_return_investigation unless the user explicitly asks for policy/eligibility investigation. "
                        "If active_case is present, you must mention that case number in your reply."
                    )
                )
            )
        elif user is not None and user.role in {
            UserRole.RETURNS_SUPERVISOR,
            UserRole.ADMINISTRATOR,
        }:
            messages.append(
                SystemMessage(
                    content=(
                        f"Active return_id={focus_return}. "
                        "Use LIVE WORKFLOW SNAPSHOT for status; call get_return_workflow_status if the user "
                        "just acted on the dashboard. For approve/reject questions, check supervisor_pending "
                        "and inspection_count before recommending."
                    )
                )
            )
        elif user is not None and user.role == UserRole.RETURNS_ANALYST:
            messages.append(
                SystemMessage(
                    content=(
                        f"Active return_id={focus_return}. "
                        "For status or 'what stage' questions, call get_return_workflow_status first "
                        "(then get_inspection_results). "
                        "If warehouse_work_complete is true, do not say warehouse is still evaluating — "
                        "say inspection is on file and state analyst_workflow_stage. "
                        "return_status 'investigating' means with the returns analyst after warehouse, not pending warehouse."
                    )
                )
            )
        else:
            messages.append(
                SystemMessage(
                    content=(
                        f"Active return_id={focus_return}. "
                        "Start with get_return_workflow_status or run_return_investigation and/or get_return_details "
                        "unless the user only asked for documents."
                    )
                )
            )
    for turn in trim_history(conversation_history):
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    messages.append(HumanMessage(content=user_message))
    return messages, focus_return


def _text_from_message_chunk(chunk: AIMessageChunk) -> str:
    content = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if block.get("type") == "text" and text:
                    parts.append(str(text))
        return "".join(parts)
    return ""


def _is_user_visible_answer_chunk(chunk: AIMessageChunk, metadata: dict[str, Any] | None) -> bool:
    """Stream only final assistant prose, not tool-planning turns."""
    if chunk.tool_call_chunks:
        return False
    if chunk.tool_calls:
        return False
    node = (metadata or {}).get("langgraph_node")
    if node is not None and node != "agent":
        return False
    return bool(_text_from_message_chunk(chunk))


def _finalize_run(
    final_messages: list,
    focus_return: str | None,
    provider_id: str,
    user: CurrentUser | None = None,
) -> dict[str, Any]:
    # Workflow = everything after the last HumanMessage that is the current user turn
    workflow_start = 0
    for i in range(len(final_messages) - 1, -1, -1):
        if isinstance(final_messages[i], HumanMessage):
            workflow_start = i + 1
            break

    workflow = final_messages[workflow_start:]
    final_text = ""
    for message in reversed(final_messages):
        if isinstance(message, AIMessage) and message.content:
            final_text = str(message.content)
            break

    role = user.role if user is not None else None
    final_text = format_operator_response(final_text, role=role)

    tool_events = enrich_tool_events_with_documents(collect_tool_events(final_messages))
    supporting_evidence = build_supporting_evidence(tool_events)
    visuals = build_visuals(tool_events, focus_return)
    agent_steps = build_agent_steps(workflow, include_synthesis=True)

    return {
        "final_response": final_text,
        "tool_events": tool_events,
        "supporting_evidence": supporting_evidence,
        "document_sources": supporting_evidence["documents"],
        "agent_steps": agent_steps,
        "visuals": visuals,
        "inferred_return_id": focus_return,
        "message_count": len(final_messages),
        "llm_provider": provider_id,
    }


def _pre_model_trim(state: dict[str, Any], *, provider_id: str) -> dict[str, Any]:
    """LangGraph hook: compress message list before each LLM call (state kept intact)."""
    messages = list(state.get("messages") or [])
    if not messages:
        return {}
    trimmed = fit_messages_to_context_budget(messages, provider_id=provider_id)
    if trimmed == messages:
        return {}
    return {"llm_input_messages": trimmed}


def _role_cache_key(user: CurrentUser | None) -> str:
    if user is None:
        return "anonymous"
    return user.role.value


@lru_cache
def get_agent_graph(provider: str, role_key: str):
    provider_id = normalize_provider(provider)
    model = get_chat_model(provider_id)
    from app.models.enums import UserRole

    role = UserRole(role_key) if role_key != "anonymous" else None
    tools = filter_tools_for_role(list(ALL_TOOLS), role)

    def pre_model_hook(state: dict[str, Any]) -> dict[str, Any]:
        return _pre_model_trim(state, provider_id=provider_id)

    return create_react_agent(model, tools, pre_model_hook=pre_model_hook)


def run_agent_chat(
    user_message: str,
    *,
    return_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    llm_provider: str | None = None,
    db: Session | None = None,
    user: CurrentUser | None = None,
) -> dict[str, Any]:
    provider_id = normalize_provider(llm_provider)
    graph = get_agent_graph(provider_id, _role_cache_key(user))
    apply_agent_context_if_provided(None, user)
    snap_db = None
    if db is not None:
        from app.database.session import get_session_maker

        snap_db = get_session_maker()()
    try:
        messages, focus_return = build_initial_messages(
            user_message,
            return_id=return_id,
            conversation_history=conversation_history,
            user=user,
            db=snap_db if snap_db is not None else db,
        )
    finally:
        if snap_db is not None:
            snap_db.close()

    run_config = agent_run_config(None, user)
    if run_config:
        result = graph.invoke({"messages": messages}, config=run_config)
    else:
        result = graph.invoke({"messages": messages})
    final_messages = result.get("messages", [])
    return _finalize_run(final_messages, focus_return, provider_id, user=user)


def stream_agent_chat(
    user_message: str,
    *,
    return_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    llm_provider: str | None = None,
    db: Session | None = None,
    user: CurrentUser | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield SSE-friendly event dicts: step updates and a final done payload."""
    provider_id = normalize_provider(llm_provider)
    graph = get_agent_graph(provider_id, _role_cache_key(user))
    apply_agent_context_if_provided(None, user)
    snap_db = None
    if db is not None:
        from app.database.session import get_session_maker

        snap_db = get_session_maker()()
    try:
        messages, focus_return = build_initial_messages(
            user_message,
            return_id=return_id,
            conversation_history=conversation_history,
            user=user,
            db=snap_db if snap_db is not None else db,
        )
    finally:
        if snap_db is not None:
            snap_db.close()
    input_len = len(messages)
    yield {"event": "status", "data": {"phase": "started", "title": "Agent run started"}}

    prev_steps: list[dict[str, Any]] = []
    final_messages: list = messages

    stream_kwargs: dict[str, Any] = {"stream_mode": ["values", "messages"]}
    run_config = agent_run_config(None, user)
    if run_config:
        stream_kwargs["config"] = run_config

    for mode, payload in graph.stream({"messages": messages}, **stream_kwargs):
        apply_agent_context_if_provided(None, user)
        if mode == "messages":
            msg_chunk, metadata = payload
            if isinstance(msg_chunk, AIMessageChunk) and _is_user_visible_answer_chunk(
                msg_chunk, metadata
            ):
                delta = _text_from_message_chunk(msg_chunk)
                if delta:
                    yield {"event": "token", "data": {"delta": delta}}
            continue

        state = payload
        final_messages = state.get("messages", final_messages)
        workflow = final_messages[input_len:]
        current_steps = build_agent_steps(workflow, include_synthesis=False)
        for row in diff_steps(prev_steps, current_steps):
            yield {"event": "step", "data": row}
        prev_steps = current_steps

    apply_agent_context_if_provided(None, user)
    payload = _finalize_run(final_messages, focus_return, provider_id, user=user)
    for row in diff_steps(prev_steps, payload["agent_steps"]):
        yield {"event": "step", "data": row}

    yield {"event": "done", "data": payload}


def sse_encode(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def clear_agent_graph_cache() -> None:
    get_agent_graph.cache_clear()
