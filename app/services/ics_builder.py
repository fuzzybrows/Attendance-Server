"""Shared ICS calendar generation utilities.

Used by:
  - /calendar/sync/{member_id}.ics  (UI subscription feed)
  - /calendar/schedule/notify        (email attachment)
"""

from datetime import datetime, timedelta, timezone
from icalendar import Calendar, Event


DEFAULT_DURATION = timedelta(hours=3)


def build_ics_event(
    *,
    summary: str,
    start: datetime,
    end: datetime = None,
    uid: str,
    description: str = "",
    session_type: str = None,
) -> Event:
    """
    Build a single iCalendar Event component.

    Args:
        summary: Event title (e.g. "Serving as Soprano - Sunday Service")
        start: Start datetime (timezone-aware)
        end: End datetime. Defaults to start + 3h if not provided.
        uid: Globally unique identifier for this event
        description: Event description text
        session_type: Optional session type for color/category tagging
    """
    event = Event()
    end = end or start + DEFAULT_DURATION

    event.add('summary', summary)
    event.add('dtstart', start)
    event.add('dtend', end)
    event.add('dtstamp', datetime.now(timezone.utc))
    event.add('uid', uid)
    event.add('description', description)

    # Add color coding based on session type
    if session_type:
        type_lower = session_type.lower()
        if type_lower == 'event':
            event.add('color', '#9C27B0')  # Purple
            event.add('categories', 'Event')
        elif type_lower == 'rehearsal':
            event.add('color', '#FF9800')  # Orange
            event.add('categories', 'Rehearsal')
        else:
            event.add('color', '#2196F3')  # Blue
            event.add('categories', 'Service')

    return event


def build_member_ics(
    *,
    member_name: str,
    calendar_title: str = None,
    assignments: list,
    prodid: str = "-//Attendance//Calendar//EN",
) -> bytes:
    """
    Build a complete .ics file for a member's assignments.

    Args:
        member_name: Display name for the calendar title
        calendar_title: Optional custom calendar title. Defaults to "{member_name}'s Schedule"
        assignments: List of dicts with keys:
            - session_title (str)
            - role (str)
            - start_time (datetime, timezone-aware)
            - end_time (datetime or None)
            - uid (str) — unique event identifier
            - session_type (str, optional) — for color/category tagging
        prodid: Product identifier for the calendar

    Returns:
        bytes: The .ics file content
    """
    cal = Calendar()
    cal.add('prodid', prodid)
    cal.add('version', '2.0')

    title = calendar_title or f"{member_name}'s Schedule"
    cal.add('name', title)
    cal.add('x-wr-calname', title)

    for a in assignments:
        role_display = a['role'].replace('_', ' ').title()
        event = build_ics_event(
            summary=f"Serving as {role_display} - {a['session_title']}",
            start=a['start_time'],
            end=a.get('end_time'),
            uid=a['uid'],
            description=f"You are scheduled to serve as {role_display} for {a['session_title']}.",
            session_type=a.get('session_type'),
        )
        cal.add_component(event)

    return cal.to_ical()
