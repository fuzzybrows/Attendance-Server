from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import random
import secrets
import io
import csv
import calendar
from collections import defaultdict
from icalendar import Calendar, Event

from app.core.database import get_db
from app.settings import settings
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

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


LOCAL_TZ = ZoneInfo(settings.app_timezone)

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

@router.get("/availability/team/{year}/{month}")
def get_team_availability(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_schedule_read_manager)
):
    """
    Get aggregated team availability for a month.
    Combines session-level opt-outs and day-level DayOff records.
    Returns member list, per-session opt-outs, and per-day aggregates.
    (Admin only)
    """
    import calendar as cal_module

    # 1. Get all active members
    all_members = db.query(Member).filter(Member.is_active == True).order_by(Member.last_name, Member.first_name).all()
    total_members = len(all_members)
    member_name_map = {m.id: f"{m.first_name} {m.last_name}" for m in all_members}

    # 2. Get all sessions in that month
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month
    ).order_by(SessionModel.start_time).all()

    session_ids = [s.id for s in sessions]

    # 3. Get all session-level opt-outs
    availabilities = db.query(Availability).filter(
        Availability.session_id.in_(session_ids)
    ).all()

    opt_outs_by_session = defaultdict(set)
    for av in availabilities:
        if not av.is_available:
            opt_outs_by_session[av.session_id].add(av.member_id)

    # 4. Get all day-level unavailability (DayOff records)
    day_offs = db.query(DayOff).filter(
        extract('year', DayOff.date) == year,
        extract('month', DayOff.date) == month,
        DayOff.is_available == False
    ).all()

    day_offs_by_date = defaultdict(set)
    for do in day_offs:
        day_offs_by_date[str(do.date)].add(do.member_id)

    # 5. Build per-session response (combine session opt-outs with day-level)
    sessions_response = []
    for s in sessions:
        session_date_str = s.start_time.strftime('%Y-%m-%d')
        # Union of session-level and day-level opt-outs
        combined_opted_out = opt_outs_by_session[s.id] | day_offs_by_date.get(session_date_str, set())
        available_count = total_members - len(combined_opted_out)

        sessions_response.append({
            "id": s.id,
            "title": s.title,
            "start_time": s.start_time.isoformat(),
            "opted_out_ids": list(combined_opted_out),
            "opted_out_members": [
                {"id": mid, "name": member_name_map.get(mid, "Unknown")}
                for mid in combined_opted_out
            ],
            "available_count": max(available_count, 0),
            "total": total_members
        })

    # 6. Build per-day aggregates
    # Get all dates in the month that have either sessions or day-offs
    num_days = cal_module.monthrange(year, month)[1]
    days_response = {}
    for day_num in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day_num:02d}"
        # Collect all unavailable member IDs for this day
        unavailable_ids = set(day_offs_by_date.get(date_str, set()))
        # Also check session-level opt-outs for sessions on this day
        for s in sessions:
            if s.start_time.strftime('%Y-%m-%d') == date_str:
                unavailable_ids |= opt_outs_by_session[s.id]

        if unavailable_ids:
            days_response[date_str] = {
                "available": total_members - len(unavailable_ids),
                "unavailable": len(unavailable_ids),
                "unavailable_members": [
                    {"id": mid, "name": member_name_map.get(mid, "Unknown")}
                    for mid in unavailable_ids
                ]
            }

    return {
        "total_members": total_members,
        "members": [
            {"id": m.id, "name": f"{m.first_name} {m.last_name}"}
            for m in all_members
        ],
        "sessions": sessions_response,
        "days": days_response
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
    assignable_roles = db.query(Role).filter(Role.display_order.isnot(None)).order_by(Role.display_order.asc()).all()
    REQUIRED_ROLES = [r.name for r in assignable_roles]
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
        role_map = defaultdict(list)
        for a in assignments_by_session[session.id]:
            role_map[a.role].append(f"{a.member.first_name} {a.member.last_name}")
        # Convert UTC to Austin time for export
        local_start = session.start_time.astimezone(LOCAL_TZ)
        writer.writerow([
            local_start.strftime("%Y-%m-%d %H:%M"),
            session.title,
            "\n".join(role_map.get("lead_singer", [])) or "Unassigned",
            "\n".join(role_map.get("soprano", [])) or "Unassigned",
            "\n".join(role_map.get("alto", [])) or "Unassigned",
            "\n".join(role_map.get("tenor", [])) or "Unassigned"
        ])

    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="choir_schedule_{year}_{month}.csv"'
    }
    return StreamingResponse(output, headers=headers, media_type="text/csv")


@router.get("/availability/export_csv", response_class=StreamingResponse)
def export_availability_matrix_csv(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_schedule_read_manager)
):
    """
    Export the availability matrix as a CSV document.
    Members as rows, sessions as columns, ✓/✗ indicators.
    (Admin only)
    """
    all_members = db.query(Member).filter(Member.is_active == True).order_by(Member.last_name, Member.first_name).all()
    total_members = len(all_members)

    if total_members == 0:
        raise HTTPException(status_code=404, detail="No active members found.")

    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month
    ).order_by(SessionModel.start_time).all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this month.")

    session_ids = [s.id for s in sessions]

    availabilities = db.query(Availability).filter(
        Availability.session_id.in_(session_ids)
    ).all()

    opt_outs_by_session = defaultdict(set)
    for av in availabilities:
        if not av.is_available:
            opt_outs_by_session[av.session_id].add(av.member_id)

    day_offs = db.query(DayOff).filter(
        extract('year', DayOff.date) == year,
        extract('month', DayOff.date) == month,
        DayOff.is_available == False
    ).all()

    day_offs_by_date = defaultdict(set)
    for do in day_offs:
        day_offs_by_date[str(do.date)].add(do.member_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    header = ["Member"]
    for s in sessions:
        local_start = s.start_time.astimezone(LOCAL_TZ)
        header.append(f"{local_start.strftime('%b %d')} - {s.title}")
    writer.writerow(header)

    # Member rows
    for m in all_members:
        row = [f"{m.first_name} {m.last_name}"]
        for s in sessions:
            session_date_str = s.start_time.strftime('%Y-%m-%d')
            combined = opt_outs_by_session[s.id] | day_offs_by_date.get(session_date_str, set())
            row.append("Unavailable" if m.id in combined else "Available")
        writer.writerow(row)

    # Summary row
    summary = ["Available (Total)"]
    for s in sessions:
        session_date_str = s.start_time.strftime('%Y-%m-%d')
        combined = opt_outs_by_session[s.id] | day_offs_by_date.get(session_date_str, set())
        available_count = total_members - len(combined)
        summary.append(f"{available_count}/{total_members}")
    writer.writerow(summary)

    output.seek(0)
    headers = {
        'Content-Disposition': f'attachment; filename="availability_matrix_{year}_{month}.csv"'
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
        extract('month', SessionModel.start_time) == month,
        SessionModel.type != 'rehearsal',
        SessionModel.status.in_(['active', 'scheduled'])
    ).order_by(SessionModel.start_time).all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this month.")

    session_ids = [s.id for s in sessions]
    assignments = db.query(Assignment).filter(Assignment.session_id.in_(session_ids)).all()

    assignments_by_session = defaultdict(lambda: defaultdict(list))
    for a in assignments:
        assignments_by_session[a.session_id][a.role].append(f"{a.member.first_name} {a.member.last_name}")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center

    month_name = calendar.month_name[month]
    elements.append(Paragraph(f"Choir Schedule - {month_name} {year}", title_style))
    elements.append(Spacer(1, 0.25*inch))

    # Cell style for wrapping text in role columns
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=10, alignment=1, leading=14)

    # Table data header
    data = [["Date", "Session Title", "Lead Singer", "Soprano", "Alto", "Tenor"]]
    
    for session in sessions:
        role_map = assignments_by_session[session.id]
        # Convert UTC to Austin time for export
        local_start = session.start_time.astimezone(LOCAL_TZ)
        # Format date as "Wed, April 24 2026"
        date_str = local_start.strftime("%a, %B %d %Y")

        def role_cell(role_key):
            names = role_map.get(role_key, [])
            if not names:
                return "-"
            if len(names) == 1:
                return names[0]
            return Paragraph("<br/>".join(names), cell_style)

        data.append([
            date_str,
            session.title,
            role_cell("lead_singer"),
            role_cell("soprano"),
            role_cell("alto"),
            role_cell("tenor")
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

@router.get("/availability/export_pdf", response_class=StreamingResponse)
def export_availability_matrix_pdf(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_schedule_read_manager)
):
    """
    Export the availability matrix as a PDF document.
    Shows members vs sessions with availability status.
    (Admin only)
    """
    import calendar as cal_module

    # Get all active members
    all_members = db.query(Member).filter(Member.is_active == True).order_by(Member.last_name, Member.first_name).all()
    total_members = len(all_members)

    if total_members == 0:
        raise HTTPException(status_code=404, detail="No active members found.")

    # Get sessions
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month
    ).order_by(SessionModel.start_time).all()

    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this month.")

    session_ids = [s.id for s in sessions]

    # Get opt-outs
    availabilities = db.query(Availability).filter(
        Availability.session_id.in_(session_ids)
    ).all()

    opt_outs_by_session = defaultdict(set)
    for av in availabilities:
        if not av.is_available:
            opt_outs_by_session[av.session_id].add(av.member_id)

    # Get day-level offs
    day_offs = db.query(DayOff).filter(
        extract('year', DayOff.date) == year,
        extract('month', DayOff.date) == month,
        DayOff.is_available == False
    ).all()

    day_offs_by_date = defaultdict(set)
    for do in day_offs:
        day_offs_by_date[str(do.date)].add(do.member_id)

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.4*inch, bottomMargin=0.4*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1

    month_name = calendar.month_name[month]
    elements.append(Paragraph(f"Availability Matrix - {month_name} {year}", title_style))
    elements.append(Spacer(1, 0.15*inch))

    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7, alignment=1, leading=9)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=7, alignment=1, leading=9, textColor=colors.whitesmoke)
    name_style = ParagraphStyle('NameStyle', parent=styles['Normal'], fontSize=8, alignment=0, leading=10)

    # Header row: Member + session columns
    header = [Paragraph("Member", header_style)]
    for s in sessions:
        local_start = s.start_time.astimezone(LOCAL_TZ)
        date_label = local_start.strftime("%b %d")
        header.append(Paragraph(f"{date_label}<br/>{s.title[:12]}", header_style))
    data = [header]

    # Member rows
    for m in all_members:
        row = [Paragraph(f"{m.first_name} {m.last_name}", name_style)]
        for s in sessions:
            session_date_str = s.start_time.strftime('%Y-%m-%d')
            combined_opted_out = opt_outs_by_session[s.id] | day_offs_by_date.get(session_date_str, set())
            is_unavailable = m.id in combined_opted_out
            row.append("✗" if is_unavailable else "✓")
        data.append(row)

    # Summary row
    summary = [Paragraph("<b>Available</b>", name_style)]
    for s in sessions:
        session_date_str = s.start_time.strftime('%Y-%m-%d')
        combined_opted_out = opt_outs_by_session[s.id] | day_offs_by_date.get(session_date_str, set())
        available_count = total_members - len(combined_opted_out)
        summary.append(Paragraph(f"<b>{available_count}/{total_members}</b>", cell_style))
    data.append(summary)

    # Calculate column widths
    usable_width = 10.0 * inch  # landscape letter minus margins
    name_col_width = 1.5 * inch
    session_col_width = (usable_width - name_col_width) / len(sessions)
    col_widths = [name_col_width] + [session_col_width] * len(sessions)

    t = Table(data, repeatRows=1, colWidths=col_widths)

    # Build cell-level styles for coloring
    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.whitesmoke, colors.HexColor('#f1f5f9')]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
    ]

    # Color ✗ cells red, ✓ cells green
    for row_idx in range(1, len(data) - 1):  # skip header and summary
        for col_idx in range(1, len(sessions) + 1):
            cell_val = data[row_idx][col_idx]
            if cell_val == "✗":
                style_commands.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#dc2626')))
                style_commands.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#fef2f2')))
            elif cell_val == "✓":
                style_commands.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#16a34a')))

    t.setStyle(TableStyle(style_commands))
    elements.append(t)
    doc.build(elements)

    buffer.seek(0)
    headers = {
        'Content-Disposition': f'attachment; filename="availability_matrix_{year}_{month}.pdf"'
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
