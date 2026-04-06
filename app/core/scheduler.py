import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import Session, SessionStatus
from app.models.assignment import Assignment
from app.models.member import Member
from app.services.comm import send_reminder_email, send_reminder_sms, send_push_notification

logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()

def dispatch_24hr_reminders():
    """
    Job that runs periodically to find sessions starting in exactly 24 hours
    and sends out reminders to the assigned members.
    """
    # Use timezone-aware UTC times
    now = datetime.now(timezone.utc)
    # Looking for sessions starting between 24 hours and 24 hours + 15 mins from now
    target_start = now + timedelta(hours=24)
    target_end = target_start + timedelta(minutes=15)
    
    logger.info(f"Checking for sessions between {target_start} and {target_end}")

    db = SessionLocal()
    try:
        upcoming_sessions = db.query(Session).filter(
            Session.start_time >= target_start,
            Session.start_time < target_end,
            Session.status == SessionStatus.ACTIVE.value
        ).all()

        for session in upcoming_sessions:
            logger.info(f"Dispatching reminders for upcoming session: {session.title}")
            
            # Find assignments for this session
            assignments = db.query(Assignment).filter(Assignment.session_id == session.id).all()
            
            for assignment in assignments:
                member = assignment.member
                session_time_str = session.start_time.strftime("%A, %B %d at %I:%M %p")
                
                logger.info(f"Sent reminder to {member.first_name} for role {assignment.role}")
                
                # Send Email
                if member.email:
                    send_reminder_email(
                        to_email=member.email,
                        member_name=member.first_name,
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
                
                # Push Notification (Mocked)
                if getattr(member, 'device_token', None):
                    send_push_notification(
                        device_token=member.device_token,
                        title="Upcoming Session Reminder",
                        body=f"You are serving as {assignment.role.replace('_', ' ').title()} in 24 hours!"
                    )
    except Exception as e:
        logger.error(f"Error in dispatch_24hr_reminders: {e}", exc_info=True)
    finally:
        db.close()

def update_session_statuses():
    """
    Job that runs every 5 minutes to sweep all sessions and update their 
    statuses to active, concluded, or archived based on their start_time and end_time.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
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
            logger.info(f"Auto-marked session {session.id} as ACTIVE")

        # Mark Concluded: when now >= end_time
        active_sessions = db.query(Session).filter(
            Session.status == SessionStatus.ACTIVE.value,
            Session.end_time <= now
        ).all()
        for session in active_sessions:
            session.status = SessionStatus.CONCLUDED.value
            logger.info(f"Auto-marked session {session.id} as CONCLUDED")

        # Mark Archived: 7 days after start_time date at midnight
        concluded_sessions = db.query(Session).filter(
            Session.status == SessionStatus.CONCLUDED.value
        ).all()
        
        for session in concluded_sessions:
            import datetime as dt
            archive_threshold = datetime.combine(session.start_time.date() + timedelta(days=7), dt.time.min)
            if now >= archive_threshold:
                session.status = SessionStatus.ARCHIVED.value
                logger.info(f"Auto-marked session {session.id} as ARCHIVED")
                
        db.commit()
    except Exception as e:
        logger.error(f"Error in update_session_statuses: {e}", exc_info=True)
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
        logger.info("Background scheduler started.")

def stop_scheduler():
    """Stops the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.")
