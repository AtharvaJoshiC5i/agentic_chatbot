"""Post-check assistant prose against tool JSON (no success claims after tool errors)."""

from __future__ import annotations

import json
import re
from typing import Any

from app.models.enums import UserRole

_RECEIPT_SUCCESS_CLAIM = re.compile(
    r"\b(recorded|logged|confirmed|marked)\b[\s\S]{0,60}?\b("
    r"receipt|arrival|received at (the )?warehouse|warehouse receipt"
    r")\b",
    re.IGNORECASE,
)
_INSPECTION_SUCCESS_CLAIM = re.compile(
    r"\b(recorded|logged|completed|saved)\b[\s\S]{0,50}?\binspection\b",
    re.IGNORECASE,
)
_VERDICT_SUCCESS_CLAIM = re.compile(
    r"\b(recorded|logged|submitted)\b[\s\S]{0,50}?\bverdict\b",
    re.IGNORECASE,
)
_SERIAL_VERIFIED_CLAIM = re.compile(
    r"\b(verified|confirmed|validated|found)\b[\s\S]{0,40}?\bserial\b",
    re.IGNORECASE,
)

_MUTATING_TOOLS = frozenset(
    {
        "record_warehouse_receipt",
        "record_inspection_tool",
        "record_warehouse_verdict",
        "decline_return_request",
        "approve_refund_record",
        "decide_replacement_request",
        "send_customer_notification",
    }
)


def _parse_tool_result(event: dict[str, Any]) -> dict[str, Any] | None:
    raw = event.get("_result_content") or event.get("result_preview") or ""
    if not isinstance(raw, str):
        raw = str(raw)
    text = raw.strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _last_results_by_tool(tool_events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for event in tool_events:
        name = event.get("tool")
        if not name:
            continue
        parsed = _parse_tool_result(event)
        if parsed is not None:
            out[str(name)] = parsed
    return out


def _tool_succeeded(data: dict[str, Any]) -> bool:
    return not data.get("error")


def enforce_tool_grounding(
    text: str,
    tool_events: list[dict[str, Any]],
    *,
    role: UserRole | None,
) -> str:
    """
    If the model claims an action succeeded but the matching tool returned ``error``,
    prepend a correction block the operator cannot miss.
    """
    if not text or not text.strip():
        return text

    results = _last_results_by_tool(tool_events)
    if not results:
        return text

    corrections: list[str] = []

    receipt = results.get("record_warehouse_receipt")
    if receipt and not _tool_succeeded(receipt):
        if _RECEIPT_SUCCESS_CLAIM.search(text):
            msg = receipt.get("message") or receipt.get("error") or "unknown error"
            corrections.append(
                f"Warehouse receipt was **not** saved ({receipt.get('error')}): {msg}"
            )

    inspection = results.get("record_inspection_tool")
    if inspection and not _tool_succeeded(inspection):
        if _INSPECTION_SUCCESS_CLAIM.search(text):
            msg = inspection.get("message") or inspection.get("error") or "unknown error"
            corrections.append(
                f"Inspection was **not** saved ({inspection.get('error')}): {msg}"
            )

    verdict = results.get("record_warehouse_verdict")
    if verdict and not _tool_succeeded(verdict):
        if _VERDICT_SUCCESS_CLAIM.search(text):
            msg = verdict.get("message") or verdict.get("error") or "unknown error"
            corrections.append(f"Warehouse verdict was **not** saved: {msg}")

    unit_lookup = results.get("get_product_unit")
    if unit_lookup and unit_lookup.get("error") == "unit_not_found":
        if _SERIAL_VERIFIED_CLAIM.search(text):
            sn = unit_lookup.get("serial_number") or "that serial"
            corrections.append(
                f"`{sn}` is **not** in the product-units registry. "
                "Use the order line purchased serial or the label on the physical unit; "
                "do not state the serial was verified in inventory."
            )

    for tool_name in _MUTATING_TOOLS:
        if tool_name in {
            "record_warehouse_receipt",
            "record_inspection_tool",
            "record_warehouse_verdict",
        }:
            continue
        data = results.get(tool_name)
        if not data or _tool_succeeded(data):
            continue
        err = data.get("error") or "failed"
        if re.search(rf"\b{re.escape(tool_name.replace('_', ' '))}\b", text, re.I):
            corrections.append(f"{tool_name} failed ({err}): {data.get('message') or err}")

    if role == UserRole.WAREHOUSE_MANAGER:
        for tool_name in ("record_warehouse_receipt", "record_inspection_tool"):
            data = results.get(tool_name)
            if data and _tool_succeeded(data):
                continue
            if data and not _tool_succeeded(data):
                continue
            if tool_name == "record_warehouse_receipt" and _RECEIPT_SUCCESS_CLAIM.search(text):
                if not any("receipt was **not**" in c for c in corrections):
                    corrections.append(
                        "No successful warehouse receipt tool result this turn — "
                        "do not tell the operator receipt was recorded."
                    )
            if tool_name == "record_inspection_tool" and _INSPECTION_SUCCESS_CLAIM.search(text):
                if not any("Inspection was **not**" in c for c in corrections):
                    corrections.append(
                        "No successful inspection tool result this turn — "
                        "do not tell the operator inspection was recorded."
                    )

    if not corrections:
        return text

    block = "## Correction (system — tool results)\n" + "\n".join(f"- {line}" for line in corrections)
    return f"{block}\n\n{text.strip()}"
