"""add_granular_scheduling_permissions

Revision ID: f26d8038cc93
Revises: cc61ecf233bf
Create Date: 2026-04-02 07:50:09.271556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f26d8038cc93'
down_revision: Union[str, Sequence[str], None] = 'cc61ecf233bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Update existing legacy permissions to their new granular names
    op.execute(
        "UPDATE permissions SET name = 'schedule_read', description = 'Permission to view the schedule availability matrix.' "
        "WHERE name = 'schedule_manager'"
    )
    op.execute(
        "UPDATE permissions SET name = 'assignments_edit', description = 'Permission to save or modify draft schedule assignments.' "
        "WHERE name = 'assignment_manager'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to legacy names
    op.execute(
        "UPDATE permissions SET name = 'schedule_manager', description = 'Legacy role for schedule managers.' "
        "WHERE name = 'schedule_read'"
    )
    op.execute(
        "UPDATE permissions SET name = 'assignment_manager', description = 'Legacy role for assignment managers.' "
        "WHERE name = 'assignments_edit'"
    )
