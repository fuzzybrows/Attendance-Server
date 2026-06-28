"""add notified_at to month_locks

Revision ID: d4e5f6a7b829
Revises: c3d4e5f6a728
Create Date: 2026-06-28

Adds a notified_at column to month_locks table to track when
schedule-published notifications were sent for a given month.
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b829'
down_revision = 'c3d4e5f6a728'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('month_locks', sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('month_locks', 'notified_at')
