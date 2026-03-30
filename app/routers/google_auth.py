from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import calendar as pycalendar

from core.database import get_db
from core.auth import get_current_active_member, create_access_token
from models.member import Member
from settings import settings

import google_auth_oauthlib.flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from jose import jwt, JWTError

router = APIRouter(
    prefix="/auth/google",
    tags=["google_calendar"],
)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_client_config():
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured on the server.")
    return {
        "web": {
            "client_id": settings.google_client_id,
            "project_id": "attendance-server",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.google_client_secret,
        }
    }

def get_proxy_aware_redirect_uri(req: Request):
    """
    Construct the correct redirect URI. Use GOOGLE_REDIRECT_URI if explicitly defined 
    in the environment (ideal for split-domain deployments like Render).
    Otherwise, guess based on the host proxy headers.
    """
    if getattr(settings, "google_redirect_uri", None):
        return settings.google_redirect_uri
        
    host = req.headers.get("x-forwarded-host", req.headers.get("host", "localhost"))
    proto = req.headers.get("x-forwarded-proto", "http")
    if "8001" in host or "8000" in host:
        return f"{proto}://{host}/auth/google/callback"
    return f"{proto}://{host}/api/auth/google/callback"

@router.get("/login")
def login_google(
    request: Request,
    app_redirect: str = "/calendar",
    current_user: Member = Depends(get_current_active_member)
):
    """
    Initiate the Google OAuth 2.0 flow.
    Supports multiple clients (Web, Android, iOS) via `app_redirect`.
    """
    client_config = get_client_config()
    redirect_uri = get_proxy_aware_redirect_uri(request)
    
    # We need to pass the member ID in the state so we know who to attach the token to.
    # We also embed the app_redirect URI here so the callback knows where to send the user 
    # (e.g. attendanceapp://calendar for Android, or /calendar for Web).
    state_token = create_access_token(
        data={"sub": str(current_user.id), "type": "google_oauth_state", "app_redirect": app_redirect},
        expires_delta=timedelta(minutes=10)
    )

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state_token
    )
    flow.redirect_uri = str(redirect_uri)

    # access_type='offline' gets a refresh token
    # prompt='consent' forces the consent screen to ensure to return a refresh token
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    return {"auth_url": authorization_url}


@router.get("/callback", name="google_oauth_callback")
def google_oauth_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db)
):
    """
    Handle the callback from Google OAuth 2.0.
    """
    if error:
        # User denied access or some other error
        return RedirectResponse(url=f"/calendar?google_error={error}")

    if not code or not state:
        return RedirectResponse(url="/calendar?google_error=missing_parameters")

    # Verify the state token to get the member ID
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "google_oauth_state":
            raise JWTError()
        member_id = int(payload.get("sub"))
        app_redirect = payload.get("app_redirect", "/calendar")
    except JWTError:
        return RedirectResponse(url="/calendar?google_error=invalid_state")

    # If decoding succeeded, we can now route errors back to their specific app!
    if error:
        return RedirectResponse(url=f"{app_redirect}?google_error={error}")

    if not code or not state:
        return RedirectResponse(url=f"{app_redirect}?google_error=missing_parameters")

    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return RedirectResponse(url=f"{app_redirect}?google_error=user_not_found")

    client_config = get_client_config()
    redirect_uri = get_proxy_aware_redirect_uri(request)

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = str(redirect_uri)

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        if credentials.refresh_token:
            member.google_refresh_token = credentials.refresh_token
            db.commit()
            
    except Exception as e:
        return RedirectResponse(url=f"{app_redirect}?google_error=token_exchange_failed")

    return RedirectResponse(url=f"{app_redirect}?google_success=true")


@router.get("/events/{year}/{month}")
def get_google_calendar_events(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Fetch the member's Google Calendar events for the specified month.
    """
    if not current_user.google_refresh_token:
        return {"events": [], "connected": False}

    try:
        credentials = Credentials(
            token=None,
            refresh_token=current_user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret
        )

        service = build('calendar', 'v3', credentials=credentials)

        # Calculate time ranges for the month
        _, last_day = pycalendar.monthrange(year, month)
        time_min = datetime(year, month, 1).isoformat() + 'Z'
        time_max = datetime(year, month, last_day, 23, 59, 59).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            # Handle all-day events vs specific time events
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            formatted_events.append({
                "id": f"google_{event['id']}",
                "title": event.get('summary', 'Busy'),
                "start": start,
                "end": end,
                "is_external": True,
                "source": "google"
            })

        return {"events": formatted_events, "connected": True}

    except Exception as e:
        # If the refresh token was revoked, we should clear it
        return {"events": [], "connected": False, "error": str(e)}
