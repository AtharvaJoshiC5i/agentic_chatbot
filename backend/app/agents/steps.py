"""Structured agent run steps for UI trace (plan → tools → answer)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

TOOL_STEP_TITLES: dict[str, str] = {
    "run_return_investigation": "Run return investigation",
    "get_return_details": "Load return details",
    "get_order_details": "Load order details",
    "get_product_details": "Load product details",
    "get_delivery_status": "Check delivery status",
    "get_inspection_results": "Load inspection results",
    "get_refund_status": "Check refund status",
    "get_customer_return_history": "Review customer return history",
    "search_return_policy": "Search return policy documents",
    "search_inspection_reports": "Search inspection reports",
    "search_customer_complaints": "Search customer complaints",
    "search_warranty_documents": "Search warranty documents",
    "search_supplier_reports": "Search supplier reports",
    "resolve_applicable_policy": "Resolve applicable policy",
    "get_recovery_options": "List recovery options",
    "get_recovery_recommendation": "Score recovery recommendation",
    "submit_create_investigation_case": "Submit investigation case",
    "submit_refund_request": "Submit refund request",
    "submit_repair_recovery_task": "Submit repair recovery task",
    "get_action_request_status": "Check action request status",
}


def tool_step_title(tool_name: str | None) -> str:
    if not tool_name:
        return "Run tool"
    return TOOL_STEP_TITLES.get(tool_name, tool_name.replace("_", " ").title())


def _preview(content: Any, max_chars: int = 1200) -> str:
    text = content if isinstance(content, str) else json.dumps(content, default=str)
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _format_tool_input(args: dict[str, Any] | None) -> str | None:
    if not args:
        return None
    return json.dumps(args, indent=2, default=str)


def build_agent_steps(
    workflow_messages: list[BaseMessage],
    *,
    include_synthesis: bool = True,
) -> list[dict[str, Any]]:
    """Turn post-user LangGraph messages into an ordered step trace."""
    steps: list[dict[str, Any]] = []
    step_index = 0

    def add(**fields: Any) -> dict[str, Any]:
        nonlocal step_index
        row = {"index": step_index, "status": fields.pop("status", "completed"), **fields}
        steps.append(row)
        step_index += 1
        return row

    add(
        kind="status",
        title="Understand request",
        detail="Parse the question and load conversation context.",
    )

    pending_calls: dict[str, dict[str, Any]] = {}

    for message in workflow_messages:
        if isinstance(message, AIMessage):
            if message.tool_calls:
                tool_names = [str(c.get("name") or "tool") for c in message.tool_calls]
                plan_detail = (str(message.content).strip() if message.content else None) or (
                    f"Selected {len(tool_names)} tool(s) to gather evidence."
                )
                add(
                    kind="plan",
                    title="Plan next actions",
                    detail=plan_detail,
                    input=_format_tool_input({"tools": tool_names}),
                )
                for call in message.tool_calls:
                    call_id = str(call.get("id") or f"{call.get('name')}-{step_index}")
                    pending_calls[call_id] = {
                        "name": call.get("name"),
                        "args": call.get("args") or {},
                    }
                    add(
                        kind="tool",
                        title=tool_step_title(str(call.get("name") or "")),
                        tool=str(call.get("name") or ""),
                        input=_format_tool_input(call.get("args") or {}),
                        output=None,
                        status="running",
                    )
            elif message.content and str(message.content).strip():
                add(
                    kind="reasoning",
                    title="Agent reasoning",
                    output=_preview(message.content, 600),
                )

        if isinstance(message, ToolMessage):
            call_id = message.tool_call_id or ""
            meta = pending_calls.get(call_id, {})
            tool_name = message.name or meta.get("name")
            output = _preview(message.content)
            matched = False
            for row in reversed(steps):
                if row.get("kind") == "tool" and row.get("status") == "running" and row.get("tool") == tool_name:
                    row["status"] = "completed"
                    row["output"] = output
                    matched = True
                    break
            if not matched:
                add(
                    kind="tool",
                    title=tool_step_title(tool_name),
                    tool=tool_name,
                    input=_format_tool_input(meta.get("args")),
                    output=output,
                )

    if include_synthesis:
        add(
            kind="synthesis",
            title="Compose final response",
            detail="Summarize findings with evidence from tool outputs.",
        )

    return steps


def diff_steps(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Steps that are new or changed (for SSE)."""
    changed: list[dict[str, Any]] = []
    for i, row in enumerate(current):
        if i >= len(previous):
            changed.append(row)
            continue
        prev = previous[i]
        if prev != row:
            changed.append(row)
    return changed
