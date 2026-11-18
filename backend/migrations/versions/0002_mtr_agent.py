"""Agent credentials and test start time.

Revision ID: 0002_mtr_agent
Revises: 0001_initial
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_mtr_agent"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("credential_hash", sa.String(64), nullable=True))
    op.add_column(
        "test_sessions", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("test_sessions", "started_at")
    op.drop_column("agents", "credential_hash")
