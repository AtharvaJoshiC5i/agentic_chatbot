"""Read-only structured + document catalog for the data browser UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.tables import DocumentMetadata

# Curated order for ops users (core commerce → returns → ops → system).
STRUCTURED_TABLE_ORDER: tuple[str, ...] = (
    "customers",
    "suppliers",
    "products",
    "orders",
    "order_items",
    "deliveries",
    "returns",
    "inspections",
    "refunds",
    "investigation_cases",
    "recovery_options",
    "recovery_tasks",
    "product_units",
    "return_events",
    "action_requests",
    "audit_logs",
    "document_metadata",
    "system_alerts",
    "users",
)

TABLE_LABELS: dict[str, str] = {
    "customers": "Customers",
    "suppliers": "Suppliers",
    "products": "Products",
    "orders": "Orders",
    "order_items": "Order items",
    "deliveries": "Deliveries",
    "returns": "Returns",
    "inspections": "Inspections",
    "refunds": "Refunds",
    "investigation_cases": "Investigation cases",
    "recovery_options": "Recovery options",
    "recovery_tasks": "Recovery tasks",
    "product_units": "Product units",
    "return_events": "Return events",
    "action_requests": "Action requests",
    "audit_logs": "Audit logs",
    "document_metadata": "Document metadata (index)",
    "system_alerts": "System alerts",
    "users": "Users",
}

SENSITIVE_COLUMNS = frozenset({"password_hash"})


def _allowed_table_names() -> set[str]:
    return set(Base.metadata.tables.keys())


def _validate_table_name(table_name: str) -> str:
    name = table_name.strip().lower()
    if name not in _allowed_table_names():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown table")
    return name


def _serialize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _file_kind(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext or "unknown"


def list_structured_tables(session: Session) -> list[dict[str, Any]]:
    allowed = _allowed_table_names()
    summaries: list[dict[str, Any]] = []
    seen: set[str] = set()

    for name in STRUCTURED_TABLE_ORDER:
        if name not in allowed:
            continue
        seen.add(name)
        table = Base.metadata.tables[name]
        row_count = session.execute(select(func.count()).select_from(table)).scalar_one()
        summaries.append(
            {
                "name": name,
                "label": TABLE_LABELS.get(name, name.replace("_", " ").title()),
                "row_count": int(row_count),
                "column_count": len(table.columns),
            }
        )

    for name in sorted(allowed - seen):
        table = Base.metadata.tables[name]
        row_count = session.execute(select(func.count()).select_from(table)).scalar_one()
        summaries.append(
            {
                "name": name,
                "label": TABLE_LABELS.get(name, name.replace("_", " ").title()),
                "row_count": int(row_count),
                "column_count": len(table.columns),
            }
        )
    return summaries


def get_structured_table_rows(
    session: Session,
    table_name: str,
    *,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    name = _validate_table_name(table_name)
    table = Base.metadata.tables[name]
    columns = [col.name for col in table.columns]
    visible_columns = [c for c in columns if c not in SENSITIVE_COLUMNS]

    total = session.execute(select(func.count()).select_from(table)).scalar_one()

    order_col = None
    if table.primary_key.columns:
        order_col = list(table.primary_key.columns)[0]
    elif columns:
        order_col = table.columns[columns[0]]

    stmt = select(table)
    if order_col is not None:
        stmt = stmt.order_by(order_col)
    stmt = stmt.limit(limit).offset(offset)
    raw_rows = session.execute(stmt).mappings().all()

    rows: list[dict[str, str]] = []
    for mapping in raw_rows:
        row: dict[str, str] = {}
        for col in visible_columns:
            if col in SENSITIVE_COLUMNS:
                row[col] = "[redacted]"
            else:
                row[col] = _serialize_cell(mapping.get(col))
        rows.append(row)

    return {
        "table_name": name,
        "label": TABLE_LABELS.get(name, name.replace("_", " ").title()),
        "columns": visible_columns,
        "rows": rows,
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


def get_overview(session: Session) -> dict[str, Any]:
    tables = list_structured_tables(session)
    structured_row_count = sum(t["row_count"] for t in tables)
    doc_total = session.execute(select(func.count()).select_from(DocumentMetadata)).scalar_one()
    type_rows = session.execute(
        select(DocumentMetadata.document_type, func.count())
        .group_by(DocumentMetadata.document_type)
        .order_by(DocumentMetadata.document_type)
    ).all()
    return {
        "structured_table_count": len(tables),
        "structured_row_count": structured_row_count,
        "document_count": int(doc_total),
        "document_types": [row[0] for row in type_rows],
    }


def list_documents(
    session: Session,
    *,
    limit: int,
    offset: int,
    document_type: str | None = None,
    return_id: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    stmt = select(DocumentMetadata)
    count_stmt = select(func.count()).select_from(DocumentMetadata)

    if document_type:
        document_type = document_type.strip().lower()
        stmt = stmt.where(DocumentMetadata.document_type == document_type)
        count_stmt = count_stmt.where(DocumentMetadata.document_type == document_type)
    if return_id:
        rid = return_id.strip().upper()
        stmt = stmt.where(DocumentMetadata.return_id == rid)
        count_stmt = count_stmt.where(DocumentMetadata.return_id == rid)
    if search:
        q = f"%{search.strip()}%"
        stmt = stmt.where(DocumentMetadata.filename.ilike(q))
        count_stmt = count_stmt.where(DocumentMetadata.filename.ilike(q))

    total = session.execute(count_stmt).scalar_one()
    rows = (
        session.execute(
            stmt.order_by(DocumentMetadata.document_id).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )

    all_types = session.execute(
        select(DocumentMetadata.document_type)
        .distinct()
        .order_by(DocumentMetadata.document_type)
    ).scalars().all()

    items = [
        {
            "document_id": row.document_id,
            "filename": row.filename,
            "document_type": row.document_type,
            "return_id": row.return_id,
            "product_id": row.product_id,
            "file_path": row.file_path,
            "file_kind": _file_kind(row.filename),
            "created_at": row.created_at.isoformat(),
            "policy_version": row.policy_version,
            "effective_date": row.effective_date.isoformat() if row.effective_date else None,
        }
        for row in rows
    ]

    return {
        "items": items,
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "document_types": list(all_types),
    }
