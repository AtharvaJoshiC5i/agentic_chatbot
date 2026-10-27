"""Supporting evidence extracted from agent tool outputs."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.agents.document_citations import DOCUMENT_TOOL_NAMES, aggregate_document_sources

TOOL_TABLE_LABELS: dict[str, tuple[str, str]] = {
    "get_return_workflow_status": ("returns", "Return workflow"),
    "get_return_details": ("returns", "Return"),
    "get_order_details": ("orders", "Order"),
    "get_order_item": ("order_items", "Order item"),
    "get_product_details": ("products", "Product"),
    "get_product_unit": ("product_units", "Product unit"),
    "get_delivery_details": ("deliveries", "Delivery"),
    "get_return_shipment": ("return_shipments", "Return shipment"),
    "get_inspection_results": ("inspections", "Inspections"),
    "get_refund_status": ("refunds", "Refunds"),
    "calculate_refundable_amount": ("refunds", "Refund calculation"),
    "get_customer_return_history": ("customer_returns", "Customer return history"),
    "run_return_investigation": ("investigation", "Investigation report"),
    "get_recovery_options": ("recovery_options", "Recovery options"),
    "get_recovery_recommendation": ("recovery_recommendation", "Recovery recommendation"),
    "build_return_timeline_tool": ("return_events", "Return timeline"),
    "detect_return_inconsistencies_tool": ("returns", "Return inconsistencies"),
    "analyze_product_complaint_patterns_tool": ("customer_complaints", "Complaint patterns"),
    "get_warehouse_handoff_status_tool": ("investigation_cases", "Warehouse handoff"),
    "list_warehouse_handoffs": ("investigation_cases", "Warehouse handoffs"),
    "list_pending_approvals_tool": ("refunds", "Pending approvals"),
    "list_customer_notifications": ("customer_notifications", "Customer notifications"),
    "list_returns": ("returns", "Returns"),
    "list_refunds_awaiting_approval": ("refunds", "Refunds awaiting approval"),
    "list_open_investigation_cases": ("investigation_cases", "Open investigation cases"),
    "list_actions_for_return": ("action_requests", "Return actions"),
    "summarize_returns": ("returns", "Returns summary"),
    "get_monitoring_overview": ("system_alerts", "Monitoring overview"),
    "submit_create_investigation_case": ("investigation_cases", "Investigation case"),
    "submit_refund_request": ("refunds", "Refund request"),
    "submit_replacement_request": ("replacement_requests", "Replacement request"),
    "submit_repair_recovery_task": ("actions", "Repair task action"),
    "submit_refurbishment_task": ("action_requests", "Refurbishment task"),
    "submit_inspection_task": ("action_requests", "Inspection task"),
    "submit_supplier_return_task": ("action_requests", "Supplier return task"),
    "submit_recycle_task": ("action_requests", "Recycle task"),
    "submit_evidence_request": ("evidence_requests", "Evidence request"),
    "get_action_request_status": ("actions", "Action status"),
    "approve_refund_record": ("refunds", "Refund decision"),
    "execute_refund_payout": ("refunds", "Refund payout"),
    "execute_action_request": ("action_requests", "Action execution"),
    "approve_action_request": ("action_requests", "Action decision"),
    "assign_investigation_case": ("investigation_cases", "Case assignment"),
    "record_warehouse_receipt": ("return_shipments", "Warehouse receipt"),
    "record_inspection_tool": ("inspections", "Warehouse inspection"),
    "update_recovery_task_tool": ("recovery_tasks", "Recovery task"),
    "resolve_investigation_case": ("investigation_cases", "Case resolution"),
    "record_warehouse_verdict": ("warehouse_verdicts", "Warehouse verdict"),
    "decline_return_request": ("returns", "Return decision"),
    "decide_replacement_request": ("replacement_requests", "Replacement decision"),
    "send_customer_notification": ("customer_notifications", "Customer notification"),
}


def _flatten_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def _rows_from_dict(data: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    columns = list(data.keys())
    row = {key: _flatten_value(data[key]) for key in columns}
    return columns, [row]


def _rows_from_list(rows: list[Any]) -> tuple[list[str], list[dict[str, str]]]:
    dict_rows = [r for r in rows if isinstance(r, dict)]
    if not dict_rows:
        return ["value"], [{"value": json.dumps(rows, default=str)}]
    columns: list[str] = []
    for row in dict_rows:
        for key in row:
            if key not in columns:
                columns.append(str(key))
    table_rows: list[dict[str, str]] = []
    for row in dict_rows:
        table_rows.append({col: _flatten_value(row.get(col)) for col in columns})
    return columns, table_rows


def _evidence_id(tool: str, title: str, preview: str) -> str:
    digest = hashlib.sha256(f"{tool}:{title}:{preview[:400]}".encode()).hexdigest()[:14]
    return f"{tool}-{digest}"


def _make_item(
    *,
    tool: str,
    table_name: str,
    title: str,
    columns: list[str],
    rows: list[dict[str, str]],
    record: dict[str, Any] | None,
    preview: str,
) -> dict[str, Any]:
    return {
        "evidence_id": _evidence_id(tool, title, preview),
        "source_tool": tool,
        "table_name": table_name,
        "title": title,
        "columns": columns,
        "rows": rows,
        "record": record,
    }


def parse_structured_evidence(tool: str, preview: str) -> list[dict[str, Any]]:
    if tool in DOCUMENT_TOOL_NAMES or not preview.strip():
        return []
    try:
        payload = json.loads(preview)
    except json.JSONDecodeError:
        return []

    table_name, default_title = TOOL_TABLE_LABELS.get(tool, ("system", tool.replace("_", " ").title()))
    items: list[dict[str, Any]] = []

    if tool == "get_order_details" and isinstance(payload, dict):
        header = {k: v for k, v in payload.items() if k != "items"}
        items_list = payload.get("items") if isinstance(payload.get("items"), list) else []
        cols, rows = _rows_from_dict(header)
        if payload.get("error"):
            attempted = str(header.get("order_id") or "").strip()
            fail_title = "Order lookup failed"
            if attempted:
                fail_title = f"{fail_title} ({attempted})"
        else:
            fail_title = None
        items.append(
            _make_item(
                tool=tool,
                table_name=table_name,
                title=fail_title
                or (f"Order {header.get('order_id', '')}".strip() or default_title),
                columns=cols,
                rows=rows,
                record=header,
                preview=preview,
            )
        )
        if items_list:
            icols, irows = _rows_from_list(items_list)
            items.append(
                _make_item(
                    tool=tool,
                    table_name="order_items",
                    title="Order line items",
                    columns=icols,
                    rows=irows,
                    record={"items": items_list},
                    preview=preview + ":items",
                )
            )
        return items

    if tool == "get_customer_return_history" and isinstance(payload, dict):
        meta_cols, meta_rows = _rows_from_dict(
            {k: v for k, v in payload.items() if k != "returns"}
        )
        items.append(
            _make_item(
                tool=tool,
                table_name=table_name,
                title=default_title,
                columns=meta_cols,
                rows=meta_rows,
                record={k: v for k, v in payload.items() if k != "returns"},
                preview=preview,
            )
        )
        returns = payload.get("returns")
        if isinstance(returns, list) and returns:
            rcols, rrows = _rows_from_list(returns)
            items.append(
                _make_item(
                    tool=tool,
                    table_name="returns",
                    title="Related returns",
                    columns=rcols,
                    rows=rrows,
                    record={"returns": returns},
                    preview=preview + ":returns",
                )
            )
        return items

    if isinstance(payload, list):
        columns, rows = _rows_from_list(payload)
        return [
            _make_item(
                tool=tool,
                table_name=table_name,
                title=default_title,
                columns=columns,
                rows=rows,
                record={"items": payload},
                preview=preview,
            )
        ]

    if isinstance(payload, dict):
        columns, rows = _rows_from_dict(payload)
        title = default_title
        if payload.get("return_id"):
            title = f"{default_title} · {payload['return_id']}"
        elif payload.get("order_id"):
            title = f"{default_title} · {payload['order_id']}"
        return [
            _make_item(
                tool=tool,
                table_name=table_name,
                title=title,
                columns=columns,
                rows=rows,
                record=payload,
                preview=preview,
            )
        ]

    return []


def build_supporting_evidence(tool_events: list[dict[str, Any]]) -> dict[str, Any]:
    structured: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in tool_events:
        tool = str(event.get("tool") or "")
        preview = event.get("_result_content") or event.get("result_preview")
        if not isinstance(preview, str):
            continue
        for item in parse_structured_evidence(tool, preview):
            eid = item["evidence_id"]
            if eid in seen:
                continue
            seen.add(eid)
            structured.append(item)

    documents = aggregate_document_sources(tool_events)
    return {"structured": structured, "documents": documents}


def append_source_references(text: str, evidence: dict[str, Any]) -> str:
    """Append concise, deterministic citations for the records and documents consulted."""
    structured = evidence.get("structured") or []
    documents = evidence.get("documents") or []
    table_aliases = {
        "actions": ("action_requests",),
        "customer_returns": ("customers", "returns"),
        "investigation": ("returns", "inspections", "investigation_cases", "refunds"),
        "recovery_recommendation": ("recovery_options", "products"),
        "system": (),
        "warehouse handoff": ("investigation_cases", "return_shipments", "inspections", "warehouse_verdicts"),
        "warehouse handoffs": ("investigation_cases", "return_shipments", "inspections", "warehouse_verdicts"),
        "pending approvals": ("refunds", "replacement_requests", "action_requests"),
    }
    identifiers: dict[str, set[str]] = {}
    id_columns = (
        "return_id", "order_id", "order_item_id", "product_id", "customer_id",
        "case_id", "inspection_id", "refund_id", "replacement_id", "action_id",
        "action_request_id", "notification_id", "shipment_id", "task_id",
    )
    for item in structured:
        table = str(item.get("table_name") or "")
        source_tables = table_aliases.get(table, (table,) if table and table != "system" else ())
        item_ids = {
            str(row[column]).strip()
            for row in item.get("rows") or []
            for column in id_columns
            if row.get(column) not in (None, "")
        }
        for source_table in source_tables:
            identifiers.setdefault(source_table, set()).update(item_ids)

    filenames = list(
        dict.fromkeys(
            (str(item.get("filename")), item.get("document_id"))
            for item in documents
            if item.get("filename")
        )
    )
    if not identifiers and not filenames:
        return text

    lines = ["\n\n**Sources**"]
    if identifiers:
        table_refs = []
        for table in sorted(identifiers):
            ids = sorted(identifiers[table])
            suffix = f" ({', '.join(ids[:3])}{', …' if len(ids) > 3 else ''})" if ids else ""
            table_refs.append(f"`{table}`{suffix}")
        lines.append("- ShopSphere tables: " + ", ".join(table_refs))
    if filenames:
        lines.append(
            "- Documents: "
            + "; ".join(f"`{filename}` (document {document_id})" for filename, document_id in filenames)
        )
    return text.rstrip() + "\n" + "\n".join(lines)
