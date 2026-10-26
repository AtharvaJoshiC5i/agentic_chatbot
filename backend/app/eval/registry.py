"""Registered agent tool names for ground-truth validation."""

from __future__ import annotations

from app.agents.graph import ALL_TOOLS

# Legacy names kept in expected_tool_actions.json map to current LangGraph tools.
TOOL_ALIASES: dict[str, str] = {
    "create_investigation_case": "submit_create_investigation_case",
    "request_refund": "submit_refund_request",
    "create_repair_task": "submit_repair_recovery_task",
    "execute_approved_refund": "execute_action_request",
    "build_return_timeline": "build_return_timeline_tool",
    "detect_return_inconsistencies": "detect_return_inconsistencies_tool",
}


def registered_tool_names() -> set[str]:
    return {tool.name for tool in ALL_TOOLS}


def resolve_tool_name(name: str) -> str:
    return TOOL_ALIASES.get(name, name)
