"""fix_dayoff_dates_utc_to_local

Migration 022 ran with CAST(start_time AS DATE) which used UTC dates.
For evening sessions in CDT (UTC-5), this produced dates one day ahead
(e.g. a 19:30 CDT session stored as 00:30 UTC gave 2026-05-23 instead
of 2026-05-22). This migration corrects those DayOff records and
backfills any that were missed.

Revision ID: d8f1b3e5a247
Revises: c7e9a2d4f138
Create Date: 2026-05-04 19:57:00.000000

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f1b3e5a247'
down_revision: Union[str, None] = 'c7e9a2d4f138'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "America/Chicago")


def upgrade() -> None:
    """Fix DayOff records that were inserted with UTC dates instead of local dates.
    
    1. Delete incorrectly dated DayOff records (UTC date != local date)
    2. Re-insert with correct local dates
    """
    # Step 1: Delete DayOff records where the stored date matches the UTC date
    # of a session opt-out but NOT the local date (i.e. they were wrong).
    op.execute(f"""
        DELETE FROM day_offs d
        WHERE d.is_available = FALSE
          AND EXISTS (
              SELECT 1 FROM availabilities a
              JOIN sessions s ON s.id = a.session_id
              WHERE a.member_id = d.member_id
                AND a.is_available = FALSE
                AND d.date = CAST(s.start_time AS DATE)
                AND d.date != CAST((s.start_time AT TIME ZONE '{APP_TIMEZONE}') AS DATE)
          )
    """)

    # Step 2: Re-insert with the correct local timezone dates
    # (also catches any that were missed entirely)
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
    """No-op: cannot reliably distinguish corrected records from original ones."""
    pass
