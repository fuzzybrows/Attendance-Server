"""
Cron job endpoints — HTTP-triggered replacements for APScheduler jobs.

These endpoints can be called by:
  - Render Cron Jobs (https://docs.render.com/cronjobs)
  - GitHub Actions scheduled workflows
  - Vercel Cron (https://vercel.com/docs/cron-jobs)
  - Manual curl calls for debugging

All endpoints require a CRON_SECRET header or query parameter for auth.
"""
import logging
from fastapi import APIRouter, HTTPException, Header, Query, status
from typing import Optional

from app.core.scheduler import dispatch_24hr_reminders, update_session_statuses, dispatch_availability_reminders
from app.settings import settings

logger = logging.getLogger("cron")

router = APIRouter(
    prefix="/cron",
    tags=["cron"],
    responses={401: {"description": "Unauthorized"}},
)


def _verify_cron_secret(
    authorization: Optional[str] = Header(None),
    secret: Optional[str] = Query(None),
):
    """
    Verify the caller is authorized to trigger cron jobs.
    Accepts the secret via:
      - Authorization: Bearer <secret>  header
      - ?secret=<secret>                query param
    """
    if not settings.cron_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET not configured on the server",
        )

    token = None

    # Check Authorization header
    if authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

    # Fall back to query param
    if not token:
        token = secret

    if not token or token != settings.cron_secret:
        logger.warning("Cron endpoint called with invalid secret", extra={"type": "cron_auth_failed"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing cron secret",
        )


@router.api_route("/reminders", methods=["GET", "HEAD", "POST"])
def trigger_reminders(
    authorization: Optional[str] = Header(None),
    secret: Optional[str] = Query(None),
    session_id: Optional[int] = Query(None, description="Send reminders for a specific session"),
):
    """
    Trigger session reminders.
    
    - Without session_id: finds sessions starting in ~24 hours (scheduled mode).
    - With session_id: sends reminders for that specific session immediately.
    
    Recommended schedule: every 15 minutes (without session_id).
    """
    _verify_cron_secret(authorization, secret)
    logger.info("Cron: reminders triggered", extra={"type": "cron_trigger", "job": "reminders", "session_id": session_id})
    dispatch_24hr_reminders(session_id=session_id)
    return {"status": "ok", "job": "reminders", "session_id": session_id}


@router.api_route("/update-statuses", methods=["GET", "HEAD", "POST"])
def trigger_update_statuses(
    authorization: Optional[str] = Header(None),
    secret: Optional[str] = Query(None),
):
    """
    Sweep session statuses (scheduled → active → concluded → archived).
    Equivalent to the old APScheduler update_statuses_job (every 5 min).
    
    Recommended schedule: every 5 minutes.
    """
    _verify_cron_secret(authorization, secret)
    logger.info("Cron: update-statuses triggered", extra={"type": "cron_trigger", "job": "update_statuses"})
    update_session_statuses()
    return {"status": "ok", "job": "update_statuses"}


@router.api_route("/availability-reminders", methods=["GET", "HEAD", "POST"])
def trigger_availability_reminders(
    authorization: Optional[str] = Header(None),
    secret: Optional[str] = Query(None),
):
    """
    Send monthly availability reminder emails for the upcoming month.

    Scheduling (1st/2nd/3rd Sundays) is the caller's responsibility.
    Recommended external cron expression: ``0 8 1-21 * 0``
    """
    _verify_cron_secret(authorization, secret)
    logger.info("Cron: availability-reminders triggered", extra={"type": "cron_trigger", "job": "availability_reminders"})
    dispatch_availability_reminders()
    return {"status": "ok", "job": "availability_reminders"}


@router.api_route("/all", methods=["GET", "HEAD", "POST"])
def trigger_all_jobs(
    authorization: Optional[str] = Header(None),
    secret: Optional[str] = Query(None),
):
    """
    Run all cron jobs in sequence. Useful for a single cron trigger
    that covers everything.
    
    Recommended schedule: every 5 minutes.
    """
    _verify_cron_secret(authorization, secret)
    logger.info("Cron: all jobs triggered", extra={"type": "cron_trigger", "job": "all"})
    
    results = {}
    
    try:
        update_session_statuses()
        results["update_statuses"] = "ok"
    except Exception as e:
        logger.error(f"Cron: update_statuses failed: {e}", exc_info=True)
        results["update_statuses"] = f"error: {str(e)}"

    try:
        dispatch_24hr_reminders()
        results["reminders"] = "ok"
    except Exception as e:
        logger.error(f"Cron: reminders failed: {e}", exc_info=True)
        results["reminders"] = f"error: {str(e)}"
    
    return {"status": "ok", "jobs": results}
