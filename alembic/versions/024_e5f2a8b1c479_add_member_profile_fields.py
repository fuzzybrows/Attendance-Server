"""add_member_profile_fields

Add date of birth (month, day, year), t-shirt size, and structured
address columns to the members table.

Revision ID: e5f2a8b1c479
Revises: d8f1b3e5a247
Create Date: 2026-05-16 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f2a8b1c479'
down_revision: Union[str, None] = 'd8f1b3e5a247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('members', sa.Column('birth_month', sa.Integer(), nullable=True))
    op.add_column('members', sa.Column('birth_day', sa.Integer(), nullable=True))
    op.add_column('members', sa.Column('birth_year', sa.Integer(), nullable=True))
    op.add_column('members', sa.Column('tshirt_size', sa.String(), nullable=True))
    op.add_column('members', sa.Column('address_street', sa.String(), nullable=True))
    op.add_column('members', sa.Column('address_city', sa.String(), nullable=True))
    op.add_column('members', sa.Column('address_state', sa.String(), nullable=True))
    op.add_column('members', sa.Column('address_zip', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('members', 'address_zip')
    op.drop_column('members', 'address_state')
    op.drop_column('members', 'address_city')
    op.drop_column('members', 'address_street')
    op.drop_column('members', 'tshirt_size')
    op.drop_column('members', 'birth_year')
    op.drop_column('members', 'birth_day')
    op.drop_column('members', 'birth_month')
