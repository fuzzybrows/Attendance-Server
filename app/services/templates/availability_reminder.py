"""Monthly availability reminder email template."""

import calendar as cal_module
from datetime import date


def availability_reminder(
    member_first_name: str,
    year: int,
    month: int,
    unavailable_dates: set,
    session_dates: set,
    calendar_url: str,
):
    """
    Return (subject, plain_text, html) for the availability reminder email.

    Args:
        unavailable_dates: Set of ISO date strings the member has marked unavailable
        session_dates: Set of ISO date strings that have scheduled sessions
        calendar_url: Deep-link URL to the calendar page
    """
    month_name = cal_module.month_name[month]
    today = date.today()

    # Build calendar grid data (Sunday-first layout)
    sun_first_cal = cal_module.Calendar(firstweekday=6)
    weeks = sun_first_cal.monthdayscalendar(year, month)

    # Header row
    day_headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # Build HTML table rows
    grid_rows = ""
    for week in weeks:
        grid_rows += "<tr>"
        for day_num in week:
            if day_num == 0:
                # Empty cell (outside the month)
                grid_rows += '<td style="padding:8px;border:1px solid #2d3748;background:#1a202c;"></td>'
                continue

            date_str = f"{year}-{month:02d}-{day_num:02d}"
            current_date = date(year, month, day_num)
            is_past = current_date < today
            is_today = current_date == today
            is_session_day = date_str in session_dates
            is_unavailable = date_str in unavailable_dates

            # Determine cell styling
            if is_past:
                bg = "#1e2533"
                text_color = "#4a5568"
                indicator = ""
            elif is_unavailable:
                bg = "#742a2a"
                text_color = "#feb2b2"
                indicator = '<span style="display:block;font-size:14px;margin-top:2px;">✗</span>'
            else:
                bg = "#22543d"
                text_color = "#9ae6b4"
                indicator = '<span style="display:block;font-size:14px;margin-top:2px;">✓</span>'

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

    # Header row HTML
    header_cells = "".join(
        f'<th style="padding:8px 4px;background:#1a202c;color:#a0aec0;font-size:12px;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'
        f'border-bottom:2px solid #4f46e5;text-align:center;">{d}</th>'
        for d in day_headers
    )

    unavail_count = len(unavailable_dates - {d for d in unavailable_dates if date(year, month, int(d.split("-")[2])) < today})

    # Summary text
    if unavail_count == 0:
        summary_text = "You haven't marked any days as unavailable yet."
        summary_color = "#a0aec0"
    else:
        summary_text = f"You have <strong>{unavail_count}</strong> day(s) marked as unavailable."
        summary_color = "#feb2b2"

    subject = f"📅 {month_name} {year} Availability Reminder — Please Confirm Your Schedule"

    plain_text = (
        f"Hi {member_first_name},\n\n"
        f"This is a reminder to mark your availability for {month_name} {year}.\n\n"
        f"You currently have {len(unavailable_dates)} day(s) marked as unavailable.\n\n"
        f"Please visit {calendar_url} to update your availability.\n\n"
        f"Thank you!"
    )

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0;line-height:1.6;padding:0;margin:0;background:#0f172a;">
    <div style="max-width:600px;margin:20px auto;background:#1e293b;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.3);">

        <!-- Header -->
        <div style="background-color:#4f46e5;background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px;color:white;">
            <h1 style="margin:0;font-size:20px;font-weight:700;letter-spacing:-0.01em;">📅 {month_name} {year} — Availability Reminder</h1>
            <p style="margin:6px 0 0;font-size:15px;opacity:0.9;">Please confirm your schedule for the upcoming month</p>
        </div>

        <div style="padding:28px 32px;">

            <!-- Greeting -->
            <p style="margin:0 0 20px;font-size:15px;color:#cbd5e1;">
                Hi {member_first_name}, please take a moment to mark your availability for
                <strong style="color:white;">{month_name} {year}</strong>.
            </p>

            <!-- Calendar Grid -->
            <p style="margin:0 0 10px;font-size:17px;font-weight:700;color:white;text-align:center;">{month_name} {year}</p>
            <table style="width:100%;border-collapse:collapse;margin-bottom:20px;border-radius:8px;overflow:hidden;">
                <thead>
                    <tr>{header_cells}</tr>
                </thead>
                <tbody>
                    {grid_rows}
                </tbody>
            </table>

            <!-- Legend -->
            <div style="display:flex;gap:16px;margin-bottom:20px;font-size:13px;color:#a0aec0;">
                <span>
                    <span style="display:inline-block;width:14px;height:14px;background:#22543d;border-radius:3px;vertical-align:middle;margin-right:4px;"></span>
                    Available
                </span>
                <span>
                    <span style="display:inline-block;width:14px;height:14px;background:#742a2a;border-radius:3px;vertical-align:middle;margin-right:4px;"></span>
                    Unavailable
                </span>
            </div>

            <!-- Summary -->
            <p style="margin:0 0 24px;font-size:14px;color:{summary_color};">
                {summary_text}
            </p>

            <!-- CTA Button -->
            <div style="text-align:center;margin-bottom:8px;">
                <a href="{calendar_url}"
                   style="display:inline-block;background-color:#6366f1;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;
                          padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;
                          font-size:15px;letter-spacing:0.02em;box-shadow:0 4px 14px rgba(99,102,241,0.4);">
                    Update Your Availability →
                </a>
            </div>

        </div>

        <!-- Footer -->
        <div style="padding:16px 32px;background:#0f172a;border-top:1px solid #334155;text-align:center;">
            <p style="margin:0;font-size:12px;color:#64748b;">This is an automated reminder. Please do not reply to this email.</p>
        </div>

    </div>
</body>
</html>'''

    return subject, plain_text, html
