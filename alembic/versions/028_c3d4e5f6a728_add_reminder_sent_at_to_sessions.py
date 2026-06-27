"""add reminder_sent_at to sessions

Revision ID: c3d4e5f6a728
Revises: b2c3d4e5f627
Create Date: 2026-06-27

Adds a reminder_sent_at column to sessions table for persistent
deduplication of 24h reminders across serverless cold starts.
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a728'
down_revision = 'b2c3d4e5f627'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'reminder_sent_at')
