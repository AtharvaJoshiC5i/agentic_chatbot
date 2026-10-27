"""Add product decision audit fields used by the returns workflow."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8b2c4d6_product_decision_fields"
down_revision: Union[str, None] = "d7a1f3c2_handoff_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("decision_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("decided_by", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_column("decided_at")
        batch_op.drop_column("decided_by")
        batch_op.drop_column("decision_reason")
