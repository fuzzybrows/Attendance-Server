"""backfill_dayoff_from_session_availability

For users who marked individual sessions as unavailable (Availability
records with is_available=False) but never created a corresponding
DayOff record, insert the missing DayOff rows so day-level and
session-level data stay consistent.

Revision ID: c7e9a2d4f138
Revises: b4d8e1f2a356
Create Date: 2026-05-04 19:16:00.000000

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e9a2d4f138'
down_revision: Union[str, None] = 'b4d8e1f2a356'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "America/Chicago")


def upgrade() -> None:
    """Insert DayOff records for session-level unavailability that has
    no matching day-level record yet."""
    op.execute(f"""
        INSERT INTO day_offs (member_id, date, is_available)
        SELECT DISTINCT
            a.member_id,
            CAST((s.start_time AT TIME ZONE '{APP_TIMEZONE}') AS DATE),
            FALSE
        FROM availabilities a
        JOIN sessions s ON s.id = a.session_id
        WHERE a.is_available = FALSE
          AND NOT EXISTS (
              SELECT 1 FROM day_offs d
              WHERE d.member_id = a.member_id
                AND d.date = CAST((s.start_time AT TIME ZONE '{APP_TIMEZONE}') AS DATE)
          )
    """)


def downgrade() -> None:
    """Remove DayOff records that were backfilled by this migration.

    Only deletes records that correspond to a session-level opt-out
    and were not independently created via the day-level API
    (i.e. they have no other source of truth besides the backfill).
    """
    op.execute(f"""
        DELETE FROM day_offs d
        WHERE d.is_available = FALSE
          AND EXISTS (
              SELECT 1 FROM availabilities a
              JOIN sessions s ON s.id = a.session_id
              WHERE a.member_id = d.member_id
                AND a.is_available = FALSE
                AND CAST((s.start_time AT TIME ZONE '{APP_TIMEZONE}') AS DATE) = d.date
          )
    """)
