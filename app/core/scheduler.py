import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo

from app.core.database import SessionLocal
from app.models.session import Session, SessionStatus
from app.models.assignment import Assignment
from app.models.member import Member
from app.models.attendance import Attendance  # noqa: F401 — needed for SQLAlchemy relationship resolution
from app.services.comm import send_reminder_email, send_reminder_sms, send_push_notification
from app.settings import settings

logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()
LOCAL_TZ = ZoneInfo(settings.app_timezone)

def send_session_reminders(session: Session, db):
    """
    Send reminders to all assigned members for a given session.
    This is the core logic reused by both the scheduled job and on-demand calls.
    """
    logger.info(f"Dispatching reminders for session: {session.title}", extra={"type": "reminder_dispatch", "session_id": session.id, "session_title": session.title})

    assignments = db.query(Assignment).filter(Assignment.session_id == session.id).all()

    for assignment in assignments:
        member = assignment.member
        session_time_str = session.start_time.astimezone(LOCAL_TZ).strftime("%A, %B %d at %I:%M %p")

        logger.info(f"Sending reminder to {member.first_name} for role {assignment.role}", extra={"type": "reminder_sent", "member_id": member.id, "member_name": member.first_name, "role": assignment.role, "session_id": session.id})

        # Send Email
        if member.email:
            send_reminder_email(
                to_email=f"{member.full_name} <{member.email}>",
                member_first_name=member.first_name,
                session_title=session.title,
                role=assignment.role,
                session_time=session_time_str
            )

        # Send SMS
        if getattr(member, 'phone_number', None):
            send_reminder_sms(
                to_phone=member.phone_number,
                member_name=member.first_name,
                session_title=session.title,
                role=assignment.role,
                session_time=session_time_str
            )

        # Push Notification
        if getattr(member, 'device_token', None):
            send_push_notification(
                device_token=member.device_token,
                title="Upcoming Session Reminder",
                body=f"You are serving as {assignment.role.replace('_', ' ').title()} in 24 hours!"
            )


def dispatch_24hr_reminders(session_id: int = None):
    """
    Send reminders to assigned members.

    If session_id is provided, sends reminders for that specific session.
    Otherwise, finds all sessions starting in ~24 hours (scheduled job mode).
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
            # Scheduled job: find sessions starting between 24h and 24h15m from now
            now = datetime.now(timezone.utc)
            target_start = now + timedelta(hours=24)
            target_end = target_start + timedelta(minutes=15)

            logger.info(f"Checking for sessions between {target_start} and {target_end}", extra={"type": "reminder_check", "target_start": str(target_start), "target_end": str(target_end)})

            upcoming_sessions = db.query(Session).filter(
                Session.start_time >= target_start,
                Session.start_time < target_end,
                Session.status == SessionStatus.SCHEDULED.value
            ).all()

            for session in upcoming_sessions:
                send_session_reminders(session, db)
    except Exception as e:
        logger.error(f"Error in dispatch_24hr_reminders: {e}", exc_info=True, extra={"type": "reminder_dispatch_error", "session_id": session_id})
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
            logger.info(f"Auto-marked session {session.id} as ACTIVE", extra={"type": "session_status_update", "session_id": session.id, "new_status": "ACTIVE"})

        # Mark Concluded: when now >= end_time
        active_sessions = db.query(Session).filter(
            Session.status == SessionStatus.ACTIVE.value,
            Session.end_time <= now
        ).all()
        for session in active_sessions:
            session.status = SessionStatus.CONCLUDED.value
            logger.info(f"Auto-marked session {session.id} as CONCLUDED", extra={"type": "session_status_update", "session_id": session.id, "new_status": "CONCLUDED"})

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
                logger.info(f"Auto-marked session {session.id} as ARCHIVED", extra={"type": "session_status_update", "session_id": session.id, "new_status": "ARCHIVED"})
                
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
        
        scheduler.start()
        logger.info("Background scheduler started.", extra={"type": "scheduler_lifecycle", "action": "start"})

def stop_scheduler():
    """Stops the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.", extra={"type": "scheduler_lifecycle", "action": "stop"})
