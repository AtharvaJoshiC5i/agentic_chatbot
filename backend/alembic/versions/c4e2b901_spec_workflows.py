"""Spec workflow tables: shipments, passports, escalations, extended actions."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e2b901_spec_workflows"
down_revision: Union[str, None] = "a8c3e1f92b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ACTION_TYPES = (
    "create_case",
    "assign_case",
    "request_refund",
    "execute_refund",
    "create_repair_task",
    "create_refurbishment_task",
    "create_supplier_return",
    "create_recycle_task",
    "create_dispose_task",
    "update_case_status",
    "create_inspection_task",
    "create_evidence_request",
    "create_data_correction",
    "create_warranty_task",
    "create_replacement_request",
)

_CASE_STATUSES = (
    "open",
    "assigned",
    "in_progress",
    "awaiting_evidence",
    "ready_for_review",
    "pending_approval",
    "resolved",
    "closed",
)

_REFUND_STATUSES = (
    "requested",
    "approved",
    "processing",
    "completed",
    "failed",
    "cancelled",
    "reconciliation_required",
)


def upgrade() -> None:
    with op.batch_alter_table("action_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("approval_expires_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("document_metadata", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("access_level", sa.String(length=32), nullable=False, server_default="standard")
        )

    op.create_table(
        "return_shipments",
        sa.Column("shipment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("pickup_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tracking_id", sa.String(length=128), nullable=True),
        sa.Column("warehouse_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receipt_discrepancy", sa.Text(), nullable=True),
        sa.Column("lost_in_transit", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.PrimaryKeyConstraint("shipment_id"),
        sa.UniqueConstraint("return_id"),
    )
    with op.batch_alter_table("return_shipments", schema=None) as batch_op:
        batch_op.create_index("ix_return_shipments_return_id", ["return_id"], unique=False)

    op.create_table(
        "case_notes",
        sa.Column("note_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("author_username", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.case_id"]),
        sa.PrimaryKeyConstraint("note_id"),
    )
    with op.batch_alter_table("case_notes", schema=None) as batch_op:
        batch_op.create_index("ix_case_notes_case_id", ["case_id"], unique=False)

    op.create_table(
        "evidence_requests",
        sa.Column("request_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("request_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'rejected', 'overdue')",
            name="ck_evidence_requests_status",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.case_id"]),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.PrimaryKeyConstraint("request_id"),
    )
    with op.batch_alter_table("evidence_requests", schema=None) as batch_op:
        batch_op.create_index("ix_evidence_requests_return_id", ["return_id"], unique=False)
        batch_op.create_index("ix_evidence_requests_status", ["status"], unique=False)

    op.create_table(
        "escalations",
        sa.Column("escalation_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("related_entity", sa.String(length=64), nullable=False),
        sa.Column("related_id", sa.String(length=64), nullable=False),
        sa.Column("escalation_reason", sa.String(length=128), nullable=False),
        sa.Column("owner_username", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')",
            name="ck_escalations_status",
        ),
        sa.PrimaryKeyConstraint("escalation_id"),
        sa.UniqueConstraint(
            "related_entity",
            "related_id",
            "escalation_reason",
            "status",
            name="uq_escalations_dedup_open",
        ),
    )
    with op.batch_alter_table("escalations", schema=None) as batch_op:
        batch_op.create_index("ix_escalations_status", ["status"], unique=False)

    op.create_table(
        "monitoring_runs",
        sa.Column("run_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("findings_count", sa.Integer(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )

    op.create_table(
        "decision_passports",
        sa.Column("passport_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("markdown_report", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.PrimaryKeyConstraint("passport_id"),
        sa.UniqueConstraint("return_id", "version", name="uq_decision_passports_return_version"),
    )
    with op.batch_alter_table("decision_passports", schema=None) as batch_op:
        batch_op.create_index("ix_decision_passports_return_id", ["return_id"], unique=False)

    op.create_table(
        "replacement_requests",
        sa.Column("replacement_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("product_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("replacement_order_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested', 'approved', 'dispatched', 'completed', 'cancelled')",
            name="ck_replacement_requests_status",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.PrimaryKeyConstraint("replacement_id"),
    )
    with op.batch_alter_table("replacement_requests", schema=None) as batch_op:
        batch_op.create_index("ix_replacement_requests_return_id", ["return_id"], unique=False)

    op.create_table(
        "warranty_claims",
        sa.Column("claim_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'under_review', 'approved', 'denied', 'closed')",
            name="ck_warranty_claims_status",
        ),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.PrimaryKeyConstraint("claim_id"),
    )
    with op.batch_alter_table("warranty_claims", schema=None) as batch_op:
        batch_op.create_index("ix_warranty_claims_return_id", ["return_id"], unique=False)

    op.create_table(
        "inventory_dispositions",
        sa.Column("disposition_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("product_unit_id", sa.Integer(), nullable=True),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("recovery_task_id", sa.Integer(), nullable=True),
        sa.Column("actual_proceeds_paise", sa.Integer(), nullable=True),
        sa.Column("actual_cost_paise", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "disposition IN ('quarantine', 'reserved', 'in_repair', 'listed_for_sale', "
            "'supplier_return', 'recycled', 'disposed')",
            name="ck_inventory_dispositions_disposition",
        ),
        sa.ForeignKeyConstraint(["product_unit_id"], ["product_units.product_unit_id"]),
        sa.ForeignKeyConstraint(["recovery_task_id"], ["recovery_tasks.recovery_task_id"]),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.PrimaryKeyConstraint("disposition_id"),
    )
    with op.batch_alter_table("inventory_dispositions", schema=None) as batch_op:
        batch_op.create_index("ix_inventory_dispositions_return_id", ["return_id"], unique=False)

    _recreate_action_type_constraint()
    _recreate_case_status_constraint()
    _recreate_refund_status_constraint()


def _recreate_action_type_constraint() -> None:
    allowed = ", ".join(repr(v) for v in _ACTION_TYPES)
    with op.batch_alter_table("action_requests", schema=None) as batch_op:
        batch_op.drop_constraint("ck_action_requests_action_type", type_="check")
        batch_op.create_check_constraint(
            "ck_action_requests_action_type",
            f"action_type IN ({allowed})",
        )


def _recreate_case_status_constraint() -> None:
    allowed = ", ".join(repr(v) for v in _CASE_STATUSES)
    with op.batch_alter_table("investigation_cases", schema=None) as batch_op:
        batch_op.drop_constraint("ck_investigation_cases_case_status", type_="check")
        batch_op.create_check_constraint(
            "ck_investigation_cases_case_status",
            f"case_status IN ({allowed})",
        )


def _recreate_refund_status_constraint() -> None:
    allowed = ", ".join(repr(v) for v in _REFUND_STATUSES)
    with op.batch_alter_table("refunds", schema=None) as batch_op:
        batch_op.drop_constraint("ck_refunds_refund_status", type_="check")
        batch_op.create_check_constraint(
            "ck_refunds_refund_status",
            f"refund_status IN ({allowed})",
        )


def downgrade() -> None:
    op.drop_table("inventory_dispositions")
    op.drop_table("warranty_claims")
    op.drop_table("replacement_requests")
    op.drop_table("decision_passports")
    op.drop_table("monitoring_runs")
    op.drop_table("escalations")
    op.drop_table("evidence_requests")
    op.drop_table("case_notes")
    op.drop_table("return_shipments")
    with op.batch_alter_table("document_metadata", schema=None) as batch_op:
        batch_op.drop_column("access_level")
    with op.batch_alter_table("action_requests", schema=None) as batch_op:
        batch_op.drop_column("approval_expires_at")
