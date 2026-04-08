"""add_all_granular_permissions

Revision ID: cc61ecf233bf
Revises: 92f346574d1e
Create Date: 2026-04-02 07:27:01.667014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc61ecf233bf'
down_revision: Union[str, Sequence[str], None] = '92f346574d1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Seed full granular permissions
    permissions_table = sa.table('permissions',
        sa.Column('id', sa.Integer),
        sa.Column('name', sa.String),
        sa.Column('description', sa.String)
    )
    op.bulk_insert(permissions_table, [
        {'name': 'sessions_read', 'description': 'Permission to view the sessions list and details.'},
        {'name': 'sessions_create', 'description': 'Permission to create new individual sessions.'},
        {'name': 'sessions_edit', 'description': 'Permission to update existing individual sessions.'},
        {'name': 'sessions_delete', 'description': 'Permission to delete individual or bulk sessions.'},
        {'name': 'attendance_read', 'description': 'Access to view attendance records and overall statistics.'},
        {'name': 'attendance_write', 'description': 'Permission to manually mark or edit attendance records.'},
        {'name': 'attendance_delete', 'description': 'Permission to delete attendance records.'},
        {'name': 'members_read', 'description': 'Access to view the member directory.'},
        {'name': 'members_create', 'description': 'Permission to add new members to the system.'},
        {'name': 'members_edit', 'description': 'Permission to update existing member profiles, roles, and permissions.'},
        {'name': 'members_delete', 'description': 'Permission to remove members from the system.'},
        {'name': 'templates_manage', 'description': 'Permission to manage recurring session templates.'},
        {'name': 'schedule_generate', 'description': 'Permission to run the auto-scheduling algorithm.'},
        {'name': 'schedule_export', 'description': 'Permission to export calendar data as CSV or PDF.'},
    ])


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DELETE FROM permissions WHERE name IN ("
        "'sessions_read', 'sessions_create', 'sessions_edit', 'sessions_delete', "
        "'attendance_read', 'attendance_write', 'attendance_delete', "
        "'members_read', 'members_create', 'members_edit', 'members_delete', "
        "'templates_manage', 'schedule_generate', 'schedule_export'"
        ")"
    )
