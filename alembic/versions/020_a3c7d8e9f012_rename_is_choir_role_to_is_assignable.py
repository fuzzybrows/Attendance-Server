"""rename_is_choir_role_to_is_assignable

Revision ID: a3c7d8e9f012
Revises: 8f4b7a1c9e2d
Create Date: 2026-04-07 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c7d8e9f012'
down_revision: Union[str, Sequence[str], None] = '8f4b7a1c9e2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Replace boolean is_choir_role with integer display_order
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('display_order', sa.Integer(), nullable=True,
                                       comment="Display order for assignable roles. If set, the role is assignable in session scheduling."))

    # Migrate data: set display_order for roles that had is_choir_role=True
    op.execute(sa.text(
        "UPDATE roles SET display_order = CASE name "
        "WHEN 'lead_singer' THEN 1 "
        "WHEN 'soprano' THEN 2 "
        "WHEN 'alto' THEN 3 "
        "WHEN 'tenor' THEN 4 "
        "END "
        "WHERE is_choir_role = true"
    ))

    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_column('is_choir_role')


def downgrade() -> None:
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_choir_role', sa.Boolean(), nullable=True,
                                       comment="Whether members with this role can be assigned in session scheduling."))

    # Migrate data back: set is_choir_role=True where display_order is not null
    op.execute(sa.text("UPDATE roles SET is_choir_role = (display_order IS NOT NULL)"))

    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_column('display_order')
