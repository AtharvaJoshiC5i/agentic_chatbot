"""Persona handoff workflow: warehouse verdicts, customer notifications, decision reasons, stock."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7a1f3c2_handoff_workflow"
down_revision: Union[str, None] = "c4e2b901_spec_workflows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("stock_on_hand", sa.Integer(), nullable=False, server_default="25"))

    # Deterministic variety so the replacement stock check is meaningful: about 1 in 8 products is out of stock.
    op.execute("UPDATE products SET stock_on_hand = 0 WHERE product_id NOT LIKE 'P_R%' AND (rowid % 8) = 0")
    op.execute("UPDATE products SET stock_on_hand = 5 + ((rowid * 7) % 40) WHERE product_id NOT LIKE 'P_R%' AND (rowid % 8) <> 0")

    with op.batch_alter_table("refunds", schema=None) as batch_op:
        batch_op.add_column(sa.Column("decision_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("decided_by", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("replacement_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("requested_by", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("decision_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("decided_by", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "warehouse_verdicts",
        sa.Column("verdict_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("resolution_type", sa.String(length=16), nullable=False),
        sa.Column("feasible", sa.Boolean(), nullable=False),
        sa.Column("stock_available", sa.Boolean(), nullable=True),
        sa.Column("recommendation", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(length=64), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("resolution_type IN ('refund', 'replacement')", name="ck_warehouse_verdicts_resolution"),
        sa.CheckConstraint("recommendation IN ('proceed', 'decline')", name="ck_warehouse_verdicts_recommendation"),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.ForeignKeyConstraint(["case_id"], ["investigation_cases.case_id"]),
        sa.PrimaryKeyConstraint("verdict_id"),
    )
    with op.batch_alter_table("warehouse_verdicts", schema=None) as batch_op:
        batch_op.create_index("ix_warehouse_verdicts_return_id", ["return_id"], unique=False)

    op.create_table(
        "customer_notifications",
        sa.Column("notification_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("return_id", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_by", sa.String(length=64), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('draft', 'sent')", name="ck_customer_notifications_status"),
        sa.ForeignKeyConstraint(["return_id"], ["returns.return_id"]),
        sa.PrimaryKeyConstraint("notification_id"),
    )
    with op.batch_alter_table("customer_notifications", schema=None) as batch_op:
        batch_op.create_index("ix_customer_notifications_return_id", ["return_id"], unique=False)


def downgrade() -> None:
    op.drop_table("customer_notifications")
    op.drop_table("warehouse_verdicts")
    with op.batch_alter_table("replacement_requests", schema=None) as batch_op:
        for col in ("decided_at", "decided_by", "decision_reason", "requested_by"):
            batch_op.drop_column(col)
    with op.batch_alter_table("refunds", schema=None) as batch_op:
        for col in ("decided_at", "decided_by", "decision_reason"):
            batch_op.drop_column(col)
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_column("stock_on_hand")
