"""Assignment notification email template with calendar grid and Google Calendar links."""

import calendar as cal_module
from datetime import date, timedelta, timezone
from urllib.parse import quote


def _build_google_calendar_url(title: str, start_dt, end_dt, description: str = "") -> str:
    """Build a Google Calendar event creation URL, HTML-safe for href attributes.

    Accepts timezone-aware datetimes in any timezone — converts to UTC for the URL.
    """
    fmt = "%Y%m%dT%H%M%SZ"
    start_utc = start_dt.astimezone(timezone.utc)
    end_utc = end_dt.astimezone(timezone.utc)
    # Use &amp; so the URL is valid inside HTML href attributes.
    # Email clients may truncate URLs at unescaped & characters.
    return (
        f"https://calendar.google.com/calendar/r/eventedit"
        f"?text={quote(title)}"
        f"&amp;dates={start_utc.strftime(fmt)}/{end_utc.strftime(fmt)}"
        f"&amp;details={quote(description)}"
    )


def assignment_notification(
    member_first_name: str,
    year: int,
    month: int,
    assignments: list,
    calendar_url: str,
    ics_bytes: bytes = None,
):
    """
    Return (subject, plain_text, html, email_attachments) for the assignment notification.

    Args:
        assignments: List of dicts with keys: session_title, role, start_time, end_time
        calendar_url: Deep-link URL to the calendar page
        ics_bytes: Optional .ics file content as bytes for attachment
    """
    month_name = cal_module.month_name[month]
    today = date.today()
    has_assignments = len(assignments) > 0

    # Collect assigned dates for calendar grid highlighting
    assigned_dates = set()
    for a in assignments:
        dt = a['start_time']
        assigned_dates.add(f"{dt.year}-{dt.month:02d}-{dt.day:02d}")

    # Build calendar grid (Sunday-first)
    sun_first_cal = cal_module.Calendar(firstweekday=6)
    weeks = sun_first_cal.monthdayscalendar(year, month)
    day_headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    grid_rows = ""
    for week in weeks:
        grid_rows += "<tr>"
        for day_num in week:
            if day_num == 0:
                grid_rows += '<td style="padding:8px;border:1px solid #2d3748;background:#1a202c;"></td>'
                continue

            date_str = f"{year}-{month:02d}-{day_num:02d}"
            current_date = date(year, month, day_num)
            is_past = current_date < today
            is_today = current_date == today
            is_assigned = date_str in assigned_dates

            if is_past:
                bg = "#1e2533"
                text_color = "#4a5568"
                indicator = ""
            elif is_assigned:
                bg = "#1e3a5f"
                text_color = "#93c5fd"
                indicator = '<span style="display:block;font-size:14px;margin-top:2px;">★</span>'
            else:
                bg = "#1a202c"
                text_color = "#a0aec0"
                indicator = ""

            border = "2px solid #6366f1" if is_today else "1px solid #2d3748"
            font_weight = "700" if is_today else "500"

            grid_rows += (
                f'<td style="padding:6px 4px;border:{border};background:{bg};'
                f'text-align:center;vertical-align:top;width:14.28%;">'
                f'<span style="color:{text_color};font-size:14px;font-weight:{font_weight};">{day_num}</span>'
                f'{indicator}'
                f'</td>'
            )
        grid_rows += "</tr>"

    header_cells = "".join(
        f'<th style="padding:8px 4px;background:#1a202c;color:#a0aec0;font-size:12px;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'
        f'border-bottom:2px solid #4f46e5;text-align:center;">{d}</th>'
        for d in day_headers
    )

    # Build assignment table rows with Google Calendar links
    assignment_rows = ""
    if has_assignments:
        for a in assignments:
            dt = a['start_time']
            end = a.get('end_time') or dt + timedelta(hours=3)
            session_date = dt.strftime("%a, %b %d")
            session_time = dt.strftime("%I:%M %p")
            role_display = a['role'].replace('_', ' ').title()

            gcal_title = f"Serving as {role_display} - {a['session_title']}"
            gcal_desc = f"You are scheduled to serve as {role_display} for {a['session_title']}."
            gcal_url = _build_google_calendar_url(gcal_title, dt, end, gcal_desc)

            assignment_rows += f'''<tr>
                <td style="padding:10px 12px;border-bottom:1px solid #2d3748;color:#e2e8f0;font-size:14px;">{session_date}<br><span style="color:#94a3b8;font-size:12px;">{session_time}</span></td>
                <td style="padding:10px 12px;border-bottom:1px solid #2d3748;color:#e2e8f0;font-size:14px;">{a['session_title']}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #2d3748;color:#93c5fd;font-size:14px;font-weight:600;">{role_display}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #2d3748;text-align:center;">
                    <a href="{gcal_url}" style="color:#818cf8;font-size:12px;text-decoration:none;font-weight:600;">+ Google Cal</a>
                </td>
            </tr>'''

    # Build the assignment section
    if has_assignments:
        assignment_section = f'''
            <h2 style="margin:0 0 12px;font-size:16px;font-weight:700;color:white;">Your Assignments</h2>
            <table style="width:100%;border-collapse:collapse;margin-bottom:16px;border-radius:8px;overflow:hidden;">
                <thead>
                    <tr style="background:#0f172a;">
                        <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;border-bottom:2px solid #4f46e5;">Date</th>
                        <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;border-bottom:2px solid #4f46e5;">Session</th>
                        <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;border-bottom:2px solid #4f46e5;">Role</th>
                        <th style="padding:10px 12px;text-align:center;color:#94a3b8;font-size:12px;font-weight:600;text-transform:uppercase;border-bottom:2px solid #4f46e5;">Add</th>
                    </tr>
                </thead>
                <tbody>{assignment_rows}</tbody>
            </table>

            <!-- Calendar Add Explanation -->
            <div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:14px 16px;margin-bottom:24px;">
                <p style="margin:0 0 8px;font-size:13px;color:#94a3b8;font-weight:600;">📎 Adding to Your Calendar</p>
                <p style="margin:0 0 4px;font-size:12px;color:#94a3b8;line-height:1.5;">
                    <strong style="color:#818cf8;">+ Google Cal</strong> links above open each session directly in Google Calendar — great for phones and Chromebooks.
                </p>
                <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.5;">
                    The <strong style="color:#818cf8;">attached .ics file</strong> imports all your sessions at once into Apple Calendar, Outlook, or any calendar app on your device.
                </p>
            </div>
        '''
        greeting_detail = f'Here are your assignments for <strong style="color:white;">{month_name} {year}</strong>.'
    else:
        assignment_section = f'''
            <div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:16px;margin-bottom:24px;">
                <p style="margin:0;font-size:14px;color:#fbbf24;font-weight:500;">
                    You have no assignments for {month_name} {year}. If you believe this is an error, please contact your team lead.
                </p>
            </div>
        '''
        greeting_detail = f'The schedule for <strong style="color:white;">{month_name} {year}</strong> has been published.'

    subject = f"📅 {month_name} {year} Schedule — {'Your Assignments Are Ready' if has_assignments else 'Schedule Published'}"

    plain_text = (
        f"Hi {member_first_name},\n\n"
        f"The schedule for {month_name} {year} has been published.\n\n"
    )
    if has_assignments:
        plain_text += "Your assignments:\n"
        for a in assignments:
            dt = a['start_time']
            plain_text += f"  - {dt.strftime('%a, %b %d %I:%M %p')}: {a['session_title']} as {a['role'].replace('_', ' ').title()}\n"
    else:
        plain_text += "You have no assignments for this month.\n"
    plain_text += f"\nView the full schedule: {calendar_url}\n"

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0;line-height:1.6;padding:0;margin:0;background:#0f172a;">
    <div style="max-width:600px;margin:20px auto;background:#1e293b;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.3);">

        <!-- Header -->
        <div style="background-color:#4f46e5;background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px;color:white;">
            <h1 style="margin:0;font-size:20px;font-weight:700;letter-spacing:-0.01em;">📅 {month_name} {year} — Schedule Published</h1>
            <p style="margin:6px 0 0;font-size:15px;opacity:0.9;">Your monthly assignments are ready</p>
        </div>

        <div style="padding:28px 32px;">

            <!-- Greeting -->
            <p style="margin:0 0 20px;font-size:15px;color:#cbd5e1;">
                Hi {member_first_name}, {greeting_detail}
            </p>

            <!-- Calendar Grid -->
            <p style="margin:0 0 10px;font-size:17px;font-weight:700;color:white;text-align:center;">{month_name} {year}</p>
            <table style="width:100%;border-collapse:collapse;margin-bottom:16px;border-radius:8px;overflow:hidden;">
                <thead>
                    <tr>{header_cells}</tr>
                </thead>
                <tbody>
                    {grid_rows}
                </tbody>
            </table>

            <!-- Legend -->
            <div style="display:flex;gap:16px;margin-bottom:24px;font-size:13px;color:#a0aec0;">
                <span>
                    <span style="display:inline-block;width:14px;height:14px;background:#1e3a5f;border-radius:3px;vertical-align:middle;margin-right:4px;"></span>
                    Assigned ★
                </span>
                <span>
                    <span style="display:inline-block;width:14px;height:14px;background:#1a202c;border-radius:3px;vertical-align:middle;margin-right:4px;border:1px solid #2d3748;"></span>
                    No assignment
                </span>
            </div>

            {assignment_section}

            <!-- CTA Button -->
            <div style="text-align:center;margin-bottom:8px;">
                <a href="{calendar_url}"
                   style="display:inline-block;background-color:#6366f1;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;
                          padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;
                          font-size:15px;letter-spacing:0.02em;box-shadow:0 4px 14px rgba(99,102,241,0.4);">
                    View Full Schedule →
                </a>
            </div>

        </div>

        <!-- Footer -->
        <div style="padding:16px 32px;background:#0f172a;border-top:1px solid #334155;text-align:center;">
            <p style="margin:0;font-size:12px;color:#64748b;">This is an automated notification. Please do not reply to this email.</p>
        </div>

    </div>
</body>
</html>'''

    email_attachments = None
    if ics_bytes and has_assignments:
        email_attachments = [{
            'filename': f'schedule_{month_name.lower()}_{year}.ics',
            'content': ics_bytes,
            'mime_type': 'text/calendar',
        }]

    return subject, plain_text, html, email_attachments
