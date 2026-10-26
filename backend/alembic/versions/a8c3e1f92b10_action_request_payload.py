"""Add payload_json to action_requests for Phase 10 execution."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a8c3e1f92b10"
down_revision: Union[str, None] = "f0f5311da420"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("action_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("action_requests", schema=None) as batch_op:
        batch_op.drop_column("payload_json")
