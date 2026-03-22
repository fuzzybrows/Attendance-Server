from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
from collections import defaultdict

from core.database import get_db
from core.auth import get_current_active_member, get_admin_member
from models.member import Member, Role
from models.session import Session as SessionModel
from models.availability import Availability
from models.assignment import Assignment
from schemas.availability import AvailabilityUpdate, AvailabilitySchema
from schemas.assignment import AssignmentCreate, AssignmentSchema
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, Response
import io
import csv
from icalendar import Calendar, Event, vText
from datetime import timedelta

class DraftScheduleRequest(BaseModel):
    year: int
    month: int

class DraftAssignment(BaseModel):
    member_id: int
    member_name: str
    role: str

class DraftSessionSchedule(BaseModel):
    session_id: int
    session_title: str
    session_date: str
    assignments: List[DraftAssignment]

class DraftScheduleResponse(BaseModel):
    sessions: List[DraftSessionSchedule]

class SaveScheduleRequest(BaseModel):
    sessions: List[DraftSessionSchedule]

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


@router.get("/availability/{year}/{month}")
def get_month_availability(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_admin_member)
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
    admin: Member = Depends(get_admin_member)
):
    """
    Run algorithm to auto-schedule members to roles for non-rehearsal sessions in the specified month.
    (Admin only)
    Roles: lead_singer, soprano, alto, tenor
    """
    REQUIRED_ROLES = ["lead_singer", "soprano", "alto", "tenor"]

    # 1. Get all non-rehearsal active sessions in that month
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == request.year,
        extract('month', SessionModel.start_time) == request.month,
        SessionModel.type != 'rehearsal',
        SessionModel.status == 'active'
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
        unavailable_members = opt_outs_by_session[session.id]
        
        # Keep track of who is already scheduled in THIS session
        scheduled_in_session = set()
        session_assignments = []

        for role in REQUIRED_ROLES:
            pool = members_by_role[role]
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
            session_id=session.id,
            session_title=session.title,
            session_date=session.start_time.isoformat(),
            assignments=session_assignments
        ))

    return DraftScheduleResponse(sessions=draft_sessions)


@router.post("/schedule/save", response_model=Dict[str, str])
def save_schedule(
    request: SaveScheduleRequest,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_admin_member)
):
    """
    Save or overwrite assignments for the specific sessions.
    (Admin only)
    """
    for session_data in request.sessions:
        # First, delete existing assignments for the specific session
        db.query(Assignment).filter(Assignment.session_id == session_data.session_id).delete()
        
        # Insert new ones
        for assignment_data in session_data.assignments:
            assignment = Assignment(
                session_id=session_data.session_id,
                member_id=assignment_data.member_id,
                role=assignment_data.role
            )
            db.add(assignment)

    db.commit()
    return {"status": "success", "message": "Schedule saved successfully"}


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
            session_id=session.id,
            session_title=session.title,
            session_date=session.start_time.isoformat(),
            assignments=session_assignments
        ))

    return DraftScheduleResponse(sessions=draft_sessions)


@router.get("/schedule/export_csv", response_class=StreamingResponse)
def export_month_schedule_csv(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    admin: Member = Depends(get_admin_member)
):
    """
    Export the finalized schedule for a month to CSV.
    (Admin only)
    """
    sessions = db.query(SessionModel).filter(
        extract('year', SessionModel.start_time) == year,
        extract('month', SessionModel.start_time) == month,
        SessionModel.type != 'rehearsal',
        SessionModel.status == 'active'
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

@router.post("/sync/token")
def generate_sync_token(
    db: Session = Depends(get_db),
    current_user: Member = Depends(get_current_active_member)
):
    """
    Generate or regenerate a sync token for the current user.
    This token is used to authenticate .ics calendar subscription URLs.
    """
    import secrets
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
    now = datetime.now()
    assignments = db.query(Assignment).join(SessionModel).filter(
        Assignment.member_id == member_id,
        SessionModel.start_time >= now,
        SessionModel.status == 'active'
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
        end_time = session.start_time + duration
        
        event.add('summary', f"Serving as {assignment.role.replace('_', ' ').title()} - {session.title}")
        event.add('dtstart', session.start_time)
        event.add('dtend', end_time)
        event.add('dtstamp', datetime.now())
        event.add('uid', f"session_{session.id}_member_{member_id}@choirattendance.com")
        event.add('description', f"You are scheduled to serve as {assignment.role.replace('_', ' ').title()} for {session.title}.")
        
        cal.add_component(event)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=member_{member_id}_schedule.ics"}
    )
