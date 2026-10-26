"""Phase 2 database schema and integrity tests."""

import sqlite3

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_engine
from app.models.enums import AccountStatus, OrderStatus
from app.models.tables import Customer, Order
from app.database.base import utc_now

EXPECTED_TABLES = {
    "action_requests",
    "alembic_version",
    "audit_logs",
    "case_notes",
    "customers",
    "decision_passports",
    "deliveries",
    "document_metadata",
    "escalations",
    "evidence_requests",
    "inspections",
    "investigation_cases",
    "inventory_dispositions",
    "monitoring_runs",
    "order_items",
    "orders",
    "product_units",
    "products",
    "recovery_options",
    "recovery_tasks",
    "refunds",
    "replacement_requests",
    "return_events",
    "return_shipments",
    "returns",
    "suppliers",
    "system_alerts",
    "users",
    "warranty_claims",
}


def test_all_core_tables_exist(migrated_db) -> None:
    with sqlite3.connect(migrated_db) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    table_names = {row[0] for row in rows}
    assert EXPECTED_TABLES.issubset(table_names)


def test_foreign_keys_enforced_on_orders(db_session, sample_catalog) -> None:
    invalid_order = Order(
        order_id="O_INVALID",
        customer_id="C_DOES_NOT_EXIST",
        order_date=utc_now(),
        total_amount=100,
        order_status=OrderStatus.PLACED,
    )
    db_session.add(invalid_order)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_customer_email_unique(db_session) -> None:
    now = utc_now()
    first = Customer(
        customer_id="C_DUP_1",
        customer_name="First",
        email="duplicate@example.invalid",
        account_created_at=now,
        account_status=AccountStatus.ACTIVE,
    )
    second = Customer(
        customer_id="C_DUP_2",
        customer_name="Second",
        email="duplicate@example.invalid",
        account_created_at=now,
        account_status=AccountStatus.ACTIVE,
    )
    db_session.add_all([first, second])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_sqlite_engine_applies_foreign_key_pragma(migrated_db) -> None:
    engine = get_engine()
    with engine.connect() as connection:
        fk_enabled = connection.exec_driver_sql("PRAGMA foreign_keys").scalar()
    assert fk_enabled == 1
