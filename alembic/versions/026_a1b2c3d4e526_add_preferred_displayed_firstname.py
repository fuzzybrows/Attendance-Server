"""add preferred_displayed_firstname to members

Revision ID: a1b2c3d4e526
Revises: f3a7c9e2d815
Create Date: 2026-05-22

Adds an optional preferred_displayed_firstname column to the members table.
When set, this name is used in place of first_name across all display surfaces.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e526'
down_revision = 'f3a7c9e2d815'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'members',
        sa.Column('preferred_displayed_firstname', sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('members', 'preferred_displayed_firstname')
