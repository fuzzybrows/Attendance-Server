"""add_session_starter_permission

Revision ID: b4d8e1f2a356
Revises: a3c7d8e9f012
Create Date: 2026-04-18 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d8e1f2a356'
down_revision: Union[str, None] = 'a3c7d8e9f012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions (name, description) "
        "VALUES ('session_starter', 'Limited dashboard: view active sessions, view attendance, start QR attendance') "
        "ON CONFLICT (name) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM permissions WHERE name = 'session_starter'")
