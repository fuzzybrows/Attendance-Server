"""add sunday_qualifier_id to roles

Revision ID: f3a7c9e2d815
Revises: e5f2a8b1c479
Create Date: 2026-05-21

Adds a self-referential nullable FK on the `roles` table.
When set, members filling this role on Sundays must ALSO hold the qualifier role.
Controlled at runtime by the ENABLE_SUNDAY_POOL_FILTER setting.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a7c9e2d815'
down_revision = 'e5f2a8b1c479'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'roles',
        sa.Column(
            'sunday_qualifier_id',
            sa.Integer(),
            sa.ForeignKey('roles.id', ondelete='SET NULL'),
            nullable=True,
            comment=(
                'FK to another Role. If set, members must also hold that role '
                'to fill this slot on Sundays. Controlled by ENABLE_SUNDAY_POOL_FILTER.'
            )
        )
    )


def downgrade() -> None:
    op.drop_column('roles', 'sunday_qualifier_id')
