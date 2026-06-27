import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
from sqlalchemy import extract
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.models.session import Session, SessionStatus
from app.models.assignment import Assignment
from app.models.member import Member, Role
from app.models.availability import Availability
from app.models.day_off import DayOff
from app.models.month_lock import MonthLock
from app.models.attendance import Attendance  # noqa: F401 — needed for SQLAlchemy relationship resolution
from app.services.comm import send_reminder_email, send_reminder_sms, send_push_notification, send_leader_summary_email, send_availability_reminder_email
from app.settings import settings

logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()
LOCAL_TZ = ZoneInfo(settings.app_timezone)

def send_session_reminders(session: Session, db, send_email=True, send_sms=False, send_push=True):
    """
    Send reminders to all assigned members for a given session.
    Optionally sends a leader summary email if notify_leaders_enabled is set.
    """
    logger.info(f"Dispatching reminders for session: {session.title}", extra={"type": "reminder_dispatch", "session_id": session.id, "session_name": session.title, "session_start_date": str(session.start_time)})

    assignments = db.query(Assignment).filter(Assignment.session_id == session.id).all()

    for assignment in assignments:
        member = assignment.member
        session_time_str = session.start_time.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")

        logger.info(f"Sending reminder to {member.display_first_name} for role {assignment.role}", extra={"type": "reminder_sent", "member_id": member.id, "member_name": member.display_first_name, "role": assignment.role, "session_id": session.id, "session_name": session.title, "session_start_date": str(session.start_time)})

        # Send Email
        if member.email and send_email:
            send_reminder_email(
                to_email=f"{member.full_name} <{member.email}>",
                member_first_name=member.display_first_name,
                session_title=session.title,
                role=assignment.role,
                session_time=session_time_str
            )

        # Send SMS
        if getattr(member, 'phone_number', None) and send_sms:
            send_reminder_sms(
                to_phone=member.phone_number,
                member_name=member.display_first_name,
                session_title=session.title,
                role=assignment.role,
                session_time=session_time_str
            )

        # Push Notification
        if getattr(member, 'device_token', None) and send_push:
            send_push_notification(
                device_token=member.device_token,
                title="Upcoming Session Reminder",
                body=f"You are serving as {assignment.role.replace('_', ' ').title()} in 24 hours!"
            )

    # ── Leader Summary Email ────────────────────────────────────────────
    if settings.notify_leaders_enabled and settings.notify_leader_ids_list:
        _send_leader_summary(session, db, assignments)


def _send_leader_summary(session: Session, db, assignments):
    """Build availability data and send a summary email to each configured leader."""

    session_time_str = session.start_time.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")
    session_date = session.start_time.astimezone(LOCAL_TZ).date()

    # Build duty roster
    assignment_data = [
        {"member_name": a.member.full_name, "role": a.role}
        for a in assignments
    ]

    # Get all active members with at least one assignable role
    all_members = db.query(Member).filter(
        Member.is_active == True,
        Member.roles.any(Role.display_order.isnot(None))
    ).all()

    # Determine who is unavailable — session-level opt-outs
    session_opt_outs = db.query(Availability).filter(
        Availability.session_id == session.id,
        Availability.is_available == False
    ).all()
    unavailable_ids = {a.member_id for a in session_opt_outs}

    # Day-level unavailability (DayOff records)
    day_offs = db.query(DayOff).filter(
        DayOff.date == session_date,
        DayOff.is_available == False
    ).all()
    unavailable_ids |= {d.member_id for d in day_offs}

    available_members = []
    unavailable_members = []
    for m in all_members:
        name = m.full_name
        if m.id in unavailable_ids:
            unavailable_members.append(name)
        else:
            available_members.append(name)

    # Send to each leader
    leaders = db.query(Member).filter(
        Member.id.in_(settings.notify_leader_ids_list)
    ).all()

    for leader in leaders:
        if not leader.email:
            logger.warning(f"Leader {leader.id} has no email — skipping summary", extra={"type": "leader_summary_skip", "member_id": leader.id})
            continue
        logger.info(f"Sending leader summary to {leader.full_name}", extra={"type": "leader_summary_sent", "member_id": leader.id, "session_id": session.id})
        send_leader_summary_email(
            to_email=f"{leader.full_name} <{leader.email}>",
            leader_name=leader.display_first_name,
            session_title=session.title,
            session_time=session_time_str,
            assignments=assignment_data,
            available_members=available_members,
            unavailable_members=unavailable_members,
        )

def dispatch_24hr_reminders(session_id: int = None):
    """
    Send reminders to assigned members.

    If session_id is provided, sends reminders for that specific session.
    Otherwise, finds all sessions starting in ~24 hours (scheduled job mode).

    Uses the session.reminder_sent_at column for persistent deduplication,
    so it's safe to call from a frequent cron even across serverless cold starts.
    """
    db = SessionLocal()
    try:
        if session_id:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                logger.warning(f"Session {session_id} not found for reminders", extra={"type": "reminder_session_not_found", "session_id": session_id})
                return
            send_session_reminders(session, db)
        else:
            # Scan a wider window (24h to 24h30m) to catch sessions between cron runs
            now = datetime.now(timezone.utc)
            target_start = now + timedelta(hours=24)
            target_end = target_start + timedelta(minutes=30)

            logger.info(f"Checking for sessions between {target_start} and {target_end}", extra={"type": "reminder_check", "target_start": str(target_start), "target_end": str(target_end)})

            upcoming_sessions = db.query(Session).filter(
                Session.start_time >= target_start,
                Session.start_time < target_end,
                Session.status == SessionStatus.SCHEDULED.value,
                Session.reminder_sent_at.is_(None),  # Only sessions not yet reminded
            ).all()

            for session in upcoming_sessions:
                send_session_reminders(session, db)
                # Mark as reminded so subsequent cron invocations skip it
                session.reminder_sent_at = now
                db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in dispatch_24hr_reminders: {e}", exc_info=True, extra={"type": "reminder_dispatch_error", "session_id": session_id})
    finally:
        db.close()

def dispatch_availability_reminders(member_ids: list[int] | None = None):
    """
    Send monthly availability reminder emails prompting members to mark
    their availability for the upcoming (next) month.  Each email includes
    an HTML calendar grid showing their currently set availability.

    This function contains no scheduling logic — it sends reminders
    whenever called.  When to call it is the caller's responsibility:
      - External cron (Render): e.g. ``0 8 * * 0`` for every Sunday 8 AM
      - APScheduler fallback: CronTrigger on Sundays at 8 AM
      - Ad-hoc: POST /cron/availability-reminders

    Args:
        member_ids: If provided, only send reminders to these specific
                    member IDs instead of all eligible members.
    """
    if not settings.availability_reminders_enabled:
        logger.debug("Availability reminders disabled — skipping")
        return

    now_local = datetime.now(LOCAL_TZ)

    logger.info(
        "Dispatching availability reminders",
        extra={"type": "availability_reminder_dispatch", "member_ids": member_ids},
    )

    # Compute the upcoming (next) month
    if now_local.month == 12:
        target_year = now_local.year + 1
        target_month = 1
    else:
        target_year = now_local.year
        target_month = now_local.month + 1

    db = SessionLocal()
    try:

        # Lock check: skip if the upcoming month is explicitly locked
        lock = db.query(MonthLock).filter(
            MonthLock.year == target_year,
            MonthLock.month == target_month,
        ).first()
        if lock and lock.is_locked:
            logger.info(
                f"Upcoming month {target_year}-{target_month:02d} is locked — skipping reminders",
                extra={"type": "availability_reminder_skip_locked", "year": target_year, "month": target_month},
            )
            return

        # Get all sessions in the target month (for session_dates set)
        target_sessions = db.query(Session).filter(
            extract('year', Session.start_time) == target_year,
            extract('month', Session.start_time) == target_month,
        ).all()

        session_dates = set()
        session_ids = []
        for s in target_sessions:
            local_date = s.start_time.astimezone(LOCAL_TZ).date()
            session_dates.add(str(local_date))
            session_ids.append(s.id)

        # Get active members with at least one assignable role
        member_query = db.query(Member).filter(
            Member.is_active == True,
            Member.roles.any(Role.display_order.isnot(None)),
        )
        if member_ids:
            member_query = member_query.filter(Member.id.in_(member_ids))
        members = member_query.all()

        if not members:
            logger.info("No eligible members found — skipping availability reminders")
            return

        # Batch-load all session-level opt-outs for the target month
        session_opt_outs_by_member = defaultdict(set)
        if session_ids:
            opt_outs = db.query(Availability).filter(
                Availability.session_id.in_(session_ids),
                Availability.is_available == False,
            ).all()
            for av in opt_outs:
                # Map session_id → date
                session_obj = next((s for s in target_sessions if s.id == av.session_id), None)
                if session_obj:
                    local_date = session_obj.start_time.astimezone(LOCAL_TZ).date()
                    session_opt_outs_by_member[av.member_id].add(str(local_date))

        # Batch-load all DayOff records for the target month
        day_offs = db.query(DayOff).filter(
            extract('year', DayOff.date) == target_year,
            extract('month', DayOff.date) == target_month,
            DayOff.is_available == False,
        ).all()

        day_offs_by_member = defaultdict(set)
        for do in day_offs:
            day_offs_by_member[do.member_id].add(str(do.date))

        # Build the calendar deep-link URL
        base_url = settings.default_redirect_url.rsplit("/", 1)[0]  # strip trailing "/calendar"
        calendar_url = f"{base_url}/calendar?month={target_month}&year={target_year}"

        sent_count = 0
        for member in members:
            if not member.email:
                continue

            # Combine session-level and day-level unavailability
            unavailable_dates = session_opt_outs_by_member[member.id] | day_offs_by_member[member.id]

            logger.info(
                f"Sending availability reminder to {member.display_first_name} for {target_year}-{target_month:02d}",
                extra={
                    "type": "availability_reminder_sent",
                    "member_id": member.id,
                    "member_name": member.display_first_name,
                    "year": target_year,
                    "month": target_month,
                    "unavailable_count": len(unavailable_dates),
                },
            )

            send_availability_reminder_email(
                to_email=f"{member.full_name} <{member.email}>",
                member_first_name=member.display_first_name,
                year=target_year,
                month=target_month,
                unavailable_dates=unavailable_dates,
                session_dates=session_dates,
                calendar_url=calendar_url,
            )
            sent_count += 1

        logger.info(
            f"Availability reminders dispatched to {sent_count} member(s) for {target_year}-{target_month:02d}",
            extra={
                "type": "availability_reminder_complete",
                "sent_count": sent_count,
                "year": target_year,
                "month": target_month,
            },
        )
    except Exception as e:
        logger.error(
            f"Error in dispatch_availability_reminders: {e}",
            exc_info=True,
            extra={"type": "availability_reminder_error"},
        )
    finally:
        db.close()


def update_session_statuses():
    """
    Job that runs every 5 minutes to sweep all sessions and update their 
    statuses to active, concluded, or archived based on their start_time and end_time.
    """
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        # Mark Active: 30 mins before start_time
        active_threshold = now + timedelta(minutes=30)
        scheduled_sessions = db.query(Session).filter(
            Session.status == SessionStatus.SCHEDULED.value,
            Session.start_time <= active_threshold
        ).all()
        for session in scheduled_sessions:
            session.status = SessionStatus.ACTIVE.value
            logger.info(f"Auto-marked session {session.id} as ACTIVE", extra={"type": "session_status_update", "session_id": session.id, "session_name": session.title, "session_start_date": str(session.start_time), "new_status": "ACTIVE"})

        # Mark Concluded: when now >= end_time
        active_sessions = db.query(Session).filter(
            Session.status == SessionStatus.ACTIVE.value,
            Session.end_time <= now
        ).all()
        for session in active_sessions:
            session.status = SessionStatus.CONCLUDED.value
            logger.info(f"Auto-marked session {session.id} as CONCLUDED", extra={"type": "session_status_update", "session_id": session.id, "session_name": session.title, "session_start_date": str(session.start_time), "new_status": "CONCLUDED"})

        # Mark Archived: 7 days after start_time date at midnight
        concluded_sessions = db.query(Session).filter(
            Session.status == SessionStatus.CONCLUDED.value
        ).all()
        
        for session in concluded_sessions:
            archive_threshold = datetime.combine(
                session.start_time.date() + timedelta(days=7), time.min, tzinfo=timezone.utc
            )
            if now >= archive_threshold:
                session.status = SessionStatus.ARCHIVED.value
                logger.info(f"Auto-marked session {session.id} as ARCHIVED", extra={"type": "session_status_update", "session_id": session.id, "session_name": session.title, "session_start_date": str(session.start_time), "new_status": "ARCHIVED"})
                
        db.commit()
    except Exception as e:
        logger.error(f"Error in update_session_statuses: {e}", exc_info=True, extra={"type": "session_status_update_error"})
    finally:
        db.close()

def start_scheduler():
    """Starts the APScheduler background tasks."""
    if not scheduler.running:
        # Run every 15 minutes
        scheduler.add_job(
            dispatch_24hr_reminders,
            trigger=IntervalTrigger(minutes=15),
            id="reminder_job",
            name="Dispatch 24-hour reminders",
            replace_existing=True
        )
        
        # Run every 5 minutes to sweep statuses
        scheduler.add_job(
            update_session_statuses,
            trigger=IntervalTrigger(minutes=5),
            id="update_statuses_job",
            name="Update session statuses",
            replace_existing=True
        )

        # Run on Sundays at 8 AM (local dev fallback).
        # The function itself skips the 4th/5th Sundays (day > 21).
        # External cron deployments should use: 0 8 * * 0
        scheduler.add_job(
            dispatch_availability_reminders,
            trigger=CronTrigger(day_of_week='sun', hour=8, timezone=LOCAL_TZ),
            id="availability_reminders_job",
            name="Dispatch availability reminders",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background scheduler started.", extra={"type": "scheduler_lifecycle", "action": "start"})

def stop_scheduler():
    """Stops the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.", extra={"type": "scheduler_lifecycle", "action": "stop"})
