from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import random
import secrets
from collections import defaultdict

from app.core.database import get_db
from app.core.auth import (
    get_current_active_member, 
    get_admin_member, 
    get_schedule_read_manager, 
    get_assignments_edit_manager,
    get_schedule_generate_manager,
    get_schedule_export_manager
)
from app.models.member import Member, Role
from app.models.session import Session as SessionModel
from app.models.availability import Availability
from app.models.assignment import Assignment
from app.models.day_off import DayOff
from app.schemas.availability import AvailabilityUpdate, AvailabilitySchema
from app.schemas.assignment import AssignmentCreate, AssignmentSchema
from app.schemas.calendar import (
    DraftScheduleRequest, DraftAssignment, DraftSessionSchedule, 
    DraftScheduleResponse, SaveScheduleRequest, DayAvailabilityRequest
)
from fastapi.responses import StreamingResponse, Response
import io
import csv
import calendar
from icalendar import Calendar, Event, vText
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch


def is_month_locked(db: Session, year: int, month: int) -> bool:
    """
    Check if any assignments exist for sessions in the given month.
    If assignments exist, the month is considered 'locked' for availability changes.
    """
    locked = db.query(Assignment).join(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month
    ).first()
    return locked is not None


router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
)

@router.put("/availability", response_model=AvailabilitySchema)
def update_availability(
    availability_data: AvailabilityUpdate,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Update the current member's availability for a specific session.
    """
    # Check if session exists
    db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Lock Check: Non-admins/managers cannot change availability if month is locked
    is_admin_or_manager = any(p.name in ['admin', 'schedule_read', 'schedule_generate'] for p in current_user.permissions)
    if not is_admin_or_manager:
        session_date = db_session.start_time
        if is_month_locked(db, session_date.year, session_date.month):
            raise HTTPException(
                status_code=400, 
                detail="Availability is locked for this month because the schedule has been finalized."
            )
    
    # Check if an availability record already exists
    availability = db.query(Availability).filter(
        Availability.member_id == current_user.id,
        Availability.session_id == session_id
    ).first()

    if availability:
        availability.is_available = availability_data.is_available
    else:
        availability = Availability(
            member_id=current_user.id,
            session_id=session_id,
            is_available=availability_data.is_available
        )
        db.add(availability)
    
    db.commit()
    db.refresh(availability)
    return availability




@router.post("/availability/day")
def update_day_availability(
    request: DayAvailabilityRequest,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Mark a day as available/unavailable for the current user.
    Stores a DayOff record (works even without sessions) and also
    updates availability for any sessions that already exist on that day.
    """
    try:
        target_date = datetime.fromisoformat(request.date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Lock Check: Non-admins/managers cannot change availability if month is locked
    is_admin_or_manager = any(p.name in ['admin', 'schedule_read', 'schedule_generate'] for p in current_user.permissions)
    if not is_admin_or_manager:
        if is_month_locked(db, target_date.year, target_date.month):
            raise HTTPException(
                status_code=400, 
                detail="Availability is locked for this month because the schedule has been finalized."
            )

    # Upsert the DayOff record (day-level, independent of sessions)
    day_off = db.query(DayOff).filter(
        DayOff.member_id == current_user.id,
        DayOff.date == target_date
    ).first()
    if day_off:
        day_off.is_available = request.is_available
    else:
        day_off = DayOff(
            member_id=current_user.id,
            date=target_date,
            is_available=request.is_available
        )
        db.add(day_off)

    # Also update any existing sessions on that day
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == target_date.year,
        extract('month', SessionModel.start_time) == target_date.month,
        extract('day', SessionModel.start_time) == target_date.day,
    ).all()

    updated = []
    for session in sessions:
        availability = db.query(Availability).filter(
            Availability.member_id == current_user.id,
            Availability.session_id == session.id
        ).first()
        if availability:
            availability.is_available = request.is_available
        else:
            availability = Availability(
                member_id=current_user.id,
                session_id=session.id,
                is_available=request.is_available
            )
            db.add(availability)
        updated.append(session.id)

    db.commit()
    return {"date": str(target_date), "updated_sessions": updated, "is_available": request.is_available}


@router.get("/availability/days/{year}/{month}")
def get_unavailable_days(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Get all dates in a specific month that the current user has explicitly marked as unavailable.
    Returns a list of ISO date strings (e.g. ['2026-03-29']).
    """
    day_offs = db.query(DayOff).filter(
        DayOff.member_id == current_user.id,
        extract('year', DayOff.date) == year,
        extract('month', DayOff.date) == month,
        DayOff.is_available == False
    ).all()

    return {
        "unavailable_days": [str(d.date) for d in day_offs]
    }


@router.get("/availability/{year}/{month}")
def get_month_availability(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_schedule_read_manager)
):
    """
    Get a matrix of all member availabilities for a specific month.
    (Admin only)
    """
    # 1. Get all sessions in that month
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month
    ).order_by(SessionModel.start_time).all()

    session_ids = [s.id for s in sessions]

    # 2. Get all availabilities for these sessions
    availabilities = db.query(Availability).filter(
        Availability.session_id.in_(session_ids)
    ).all()

    # Determine who opted out
    opt_outs_by_session = {s.id: [] for s in sessions}
    for av in availabilities:
        if not av.is_available:
            opt_outs_by_session[av.session_id].append(av.member_id)

    # Note: If a record doesn't exist, we assume they ARE available (default=True).

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "start_time": s.start_time.isoformat(),
                "opted_out_member_ids": opt_outs_by_session[s.id]
            }
            for s in sessions
        ]
    }

@router.post("/schedule/generate", response_model=DraftScheduleResponse)
def generate_schedule(
    request: DraftScheduleRequest,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_schedule_generate_manager)
):
    """
    Run algorithm to auto-schedule members to roles for non-rehearsal sessions in the specified month.
    (Admin only)
    Roles: lead_singer, soprano, alto, tenor
    """
    choir_roles = db.query(Role).filter(Role.is_choir_role == True).all()
    REQUIRED_ROLES = [r.name for r in choir_roles]
    if not REQUIRED_ROLES:
        # Fallback to defaults if none marked to avoid empty schedule
        REQUIRED_ROLES = ["lead_singer", "soprano", "alto", "tenor"]

    # 1. Get all non-rehearsal active sessions in that month
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == request.year,
        extract('month', SessionModel.start_time) == request.month,
        SessionModel.type != 'rehearsal',
        SessionModel.status.in_(['active', 'scheduled'])
    ).order_by(SessionModel.start_time).all()

    session_ids = [s.id for s in sessions]

    if not sessions:
        return DraftScheduleResponse(sessions=[])

    # 2. Get all availabilities (opt-outs)
    availabilities = db.query(Availability).filter(
        Availability.session_id.in_(session_ids)
    ).all()
    opt_outs_by_session = defaultdict(set)
    for av in availabilities:
        if not av.is_available:
            opt_outs_by_session[av.session_id].add(av.member_id)

    # 2.1 Get all DayOff records for the month (unavailability)
    day_offs = db.query(DayOff).filter(
        extract('year', DayOff.date) == request.year,
        extract('month', DayOff.date) == request.month,
        DayOff.is_available == False
    ).all()
    
    day_offs_by_date = defaultdict(set)
    for do in day_offs:
        day_offs_by_date[do.date].add(do.member_id)

    # 3. Get all members and their roles
    # We only care about members who have at least one of the REQUIRED_ROLES
    members = db.query(Member).all()
    
    # Map roles to members
    members_by_role = defaultdict(list)
    for member in members:
        # Member.roles gives ORM Role objects (if we assume the lazy load works)
        # We need their string names.
        member_role_names = [r.name for r in member.roles]
        for role_name in REQUIRED_ROLES:
            if role_name in member_role_names:
                members_by_role[role_name].append(member)

    # Keep track of assignment counts to promote fair rotation
    assignment_counts = defaultdict(int)

    draft_sessions = []

    for session in sessions:
        # Combine per-session opt-outs with day-level unavailability
        session_date = session.start_time.date()
        unavailable_members = opt_outs_by_session[session.id].union(day_offs_by_date[session_date])
        
        # Keep track of who is already scheduled in THIS session
        scheduled_in_session = set()
        session_assignments = []

        for role in REQUIRED_ROLES:
            pool = members_by_role[role]
            
            if role == "lead_singer" and session_date.weekday() == 6:
                pool = [m for m in pool if any(r.name == 'Sunday Lead Singer' for r in m.roles)]
                
            # Filter pool: must not be opted out, must not be scheduled already this session
            valid_pool = [m for m in pool if m.id not in unavailable_members and m.id not in scheduled_in_session]

            if not valid_pool:
                continue # No available members for this role

            # Sort by least number of assignments this month to balance load, shuffle ties
            random.shuffle(valid_pool)
            valid_pool.sort(key=lambda m: assignment_counts[m.id])
            
            selected_member = valid_pool[0]
            
            # Record assignment
            scheduled_in_session.add(selected_member.id)
            assignment_counts[selected_member.id] += 1
            
            session_assignments.append(DraftAssignment(
                member_id=selected_member.id,
                member_name=f"{selected_member.first_name} {selected_member.last_name}",
                role=role
            ))

        draft_sessions.append(DraftSessionSchedule(
            id=session.id,
            title=session.title,
            type=session.type,
            start_time=session.start_time.isoformat(),
            assignments=session_assignments
        ))

    return DraftScheduleResponse(sessions=draft_sessions)


@router.post("/schedule/save", response_model=Dict[str, str])
def save_schedule(
    request: SaveScheduleRequest,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_assignments_edit_manager)
):
    """
    Save or overwrite assignments for the specific sessions.
    (Admin only)
    """
    for session_data in request.sessions:
        # First, delete existing assignments for the specific session
        db.query(Assignment).filter(Assignment.session_id == session_data.id).delete()
        
        # Insert new ones
        for assignment_data in session_data.assignments:
            assignment = Assignment(
                session_id=session_data.id,
                member_id=assignment_data.member_id,
                role=assignment_data.role
            )
            db.add(assignment)

    db.commit()
    return {"status": "success", "message": "Schedule saved successfully"}


@router.get("/schedule/session/{session_id}", response_model=DraftSessionSchedule)
def get_session_schedule(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Get the finalized schedule/assignments for a specific session.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    assignments = db.query(Assignment).filter(Assignment.session_id == session_id).all()

    session_assignments = []
    for a in assignments:
        session_assignments.append(DraftAssignment(
            member_id=a.member_id,
            member_name=f"{a.member.first_name} {a.member.last_name}",
            role=a.role
        ))

    return DraftSessionSchedule(
        id=session.id,
        title=session.title,
        type=session.type,
        start_time=session.start_time.isoformat(),
        assignments=session_assignments
    )


@router.get("/schedule/{year}/{month}", response_model=DraftScheduleResponse)
def get_schedule(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Get the finalized schedule for a specific month.
    (Accessible by all members)
    """
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month
    ).order_by(SessionModel.start_time).all()

    session_ids = [s.id for s in sessions]

    assignments = db.query(Assignment).filter(
        Assignment.session_id.in_(session_ids)
    ).all()

    assignments_by_session = defaultdict(list)
    for a in assignments:
        assignments_by_session[a.session_id].append(a)

    draft_sessions = []
    for session in sessions:
        session_assignments = []
        for a in assignments_by_session[session.id]:
            session_assignments.append(DraftAssignment(
                member_id=a.member_id,
                member_name=f"{a.member.first_name} {a.member.last_name}",
                role=a.role
            ))
        
        draft_sessions.append(DraftSessionSchedule(
            id=session.id,
            title=session.title,
            type=session.type,
            start_time=session.start_time.isoformat(),
            assignments=session_assignments
        ))

    return DraftScheduleResponse(sessions=draft_sessions)


@router.get("/schedule/export_csv", response_class=StreamingResponse)
def export_month_schedule_csv(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_schedule_export_manager)
):
    """
    Export the finalized schedule for a month to CSV.
    (Admin only)
    """
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month,
        SessionModel.type != 'rehearsal',
        SessionModel.status.in_(['active', 'scheduled'])
    ).order_by(SessionModel.start_time).all()

    session_ids = [s.id for s in sessions]

    assignments = db.query(Assignment).filter(
        Assignment.session_id.in_(session_ids)
    ).all()

    assignments_by_session = defaultdict(list)
    for a in assignments:
        assignments_by_session[a.session_id].append(a)

    # Generate CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Session Title", "Lead Singer", "Soprano", "Alto", "Tenor"])

    for session in sessions:
        role_map = {a.role: f"{a.member.first_name} {a.member.last_name}" for a in assignments_by_session[session.id]}
        writer.writerow([
            session.start_time.strftime("%Y-%m-%d %H:%M"),
            session.title,
            role_map.get("lead_singer", "Unassigned"),
            role_map.get("soprano", "Unassigned"),
            role_map.get("alto", "Unassigned"),
            role_map.get("tenor", "Unassigned")
        ])

    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="choir_schedule_{year}_{month}.csv"'
    }
    return StreamingResponse(output, headers=headers, media_type="text/csv")


@router.get("/schedule/export_pdf", response_class=StreamingResponse)
def export_month_schedule_pdf(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_schedule_export_manager)
):
    """
    Export the monthly schedule as a PDF document.
    (Accessible by admins only)
    """
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month
    ).order_by(SessionModel.start_time).all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this month.")

    session_ids = [s.id for s in sessions]
    assignments = db.query(Assignment).filter(Assignment.session_id.in_(session_ids)).all()

    assignments_by_session = defaultdict(lambda: defaultdict(str))
    for a in assignments:
        assignments_by_session[a.session_id][a.role] = f"{a.member.first_name} {a.member.last_name}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center

    month_name = calendar.month_name[month]
    elements.append(Paragraph(f"Choir Schedule - {month_name} {year}", title_style))
    elements.append(Spacer(1, 0.25*inch))

    # Table data header
    data = [["Date", "Session Title", "Lead Singer", "Soprano", "Alto", "Tenor"]]
    
    for session in sessions:
        role_map = assignments_by_session[session.id]
        # Format date as "Wed, April 24 2026"
        date_str = session.start_time.strftime("%a, %B %d %Y")
        data.append([
            date_str,
            session.title,
            role_map.get("lead_singer", "-"),
            role_map.get("soprano", "-"),
            role_map.get("alto", "-"),
            role_map.get("tenor", "-")
        ])

    # Table styling
    # Landscape letter is 11 inches wide. Left/right margin 0.5 each = 10 inches usable.
    t = Table(data, repeatRows=1, colWidths=[1.8*inch, 2.2*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')), # Slate 600
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')), # Slate 50
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#f1f5f9')]) # Alternate rows
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    buffer.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="choir_schedule_{year}_{month}.pdf"'
    }
    return StreamingResponse(buffer, headers=headers, media_type="application/pdf")

@router.post("/sync/token")
def generate_sync_token(
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Generate or regenerate a sync token for the current user.
    This token is used to authenticate .ics calendar subscription URLs.
    """
    token = secrets.token_urlsafe(32)
    current_user.sync_token = token
    db.commit()
    return {"sync_token": token, "sync_url": f"/calendar/sync/{current_user.id}.ics?key={token}"}


@router.get("/sync/{member_id}.ics", response_class=Response)
def sync_member_calendar(
    member_id: int,
    key: str,
    db: Session = Depends(get_db)
):
    """
    Generate an iCalendar (.ics) feed of assignments for a specific member.
    Authenticated via per-user sync token (query param) so calendar apps can poll it.
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if not member.sync_token or member.sync_token != key:
        raise HTTPException(status_code=403, detail="Invalid sync token")

    # Fetch all future assignments for this member
    now = datetime.now(timezone.utc)
    assignments = db.query(Assignment).join(SessionModel).filter(
        Assignment.member_id == member_id,
        SessionModel.start_time >= now,
        SessionModel.status.in_(['active', 'scheduled'])
    ).all()

    cal = Calendar()
    cal.add('prodid', '-//Choir Attendance//Calendar Sync//EN')
    cal.add('version', '2.0')
    cal.add('name', f"{member.first_name}'s Choir Schedule")
    cal.add('x-wr-calname', f"{member.first_name}'s Choir Schedule")

    for assignment in assignments:
        session = assignment.session
        event = Event()
        
        # Assume sessions are ~3 hours long for calendar blocking
        duration = timedelta(hours=3)
        # Session start_time is now aware
        start_utc = session.start_time
        end_utc = start_utc + duration
        
        event.add('summary', f"Serving as {assignment.role.replace('_', ' ').title()} - {session.title}")
        event.add('dtstart', start_utc)
        event.add('dtend', end_utc)
        event.add('dtstamp', datetime.now(timezone.utc))
        event.add('uid', f"session_{session.id}_member_{member_id}@choirattendance.com")
        event.add('description', f"You are scheduled to serve as {assignment.role.replace('_', ' ').title()} for {session.title}.")
        
        # Add color coding based on session type
        if session.type.lower() == 'event':
            event.add('color', '#9C27B0') # Purple
            event.add('categories', 'Event')
        elif session.type.lower() == 'rehearsal':
            event.add('color', '#FF9800') # Orange
            event.add('categories', 'Rehearsal')
        else:
            event.add('color', '#2196F3') # Blue
            event.add('categories', 'Service')
        
        cal.add_component(event)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=member_{member_id}_schedule.ics"}
    )
