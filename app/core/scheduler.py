import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, timezone

from core.database import SessionLocal
from models import Session, SessionStatus
from models.assignment import Assignment
from models.member import Member
from services.comm import send_reminder_email, send_reminder_sms, send_push_notification

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
        scheduler.start()
        logger.info("Background scheduler started.")

def stop_scheduler():
    """Stops the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped.")
