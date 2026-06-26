"""add month_locks table

Revision ID: b2c3d4e5f627
Revises: a1b2c3d4e526
Create Date: 2026-06-25

Adds a month_locks table for explicit admin-controlled availability lock
per year/month. Auto-created when assignments are saved.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f627'
down_revision = 'a1b2c3d4e526'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'month_locks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.UniqueConstraint('year', 'month', name='uq_year_month_lock'),
    )


def downgrade() -> None:
    op.drop_table('month_locks')
