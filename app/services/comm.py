import calendar as cal_module
import logging
import random

# Firebase disabled to reduce bundle size — push notifications stubbed out
# import firebase_admin
# from firebase_admin import credentials, messaging
import os
from datetime import date
from app.settings import settings
from app.services.email_providers import get_email_provider
from app.services.sms_providers import get_sms_provider

logger = logging.getLogger(__name__)

# API credentials from settings
# FIREBASE_CREDENTIALS_PATH = settings.firebase_credentials_path
ROLE_PREPOSITION = settings.role_preposition

# Module-level provider singletons
_email_provider = get_email_provider()
_sms_provider = get_sms_provider()


def _send_email(to_email: str, subject: str, plain_text: str, html: str) -> bool:
    """Send an email using the configured provider."""
    return _email_provider.send(to_email, subject, plain_text, html)


def _send_sms(to_phone: str, body: str) -> bool:
    """Send an SMS using the configured provider."""
    return _sms_provider.send(to_phone, body)


# ── Firebase (disabled) ─────────────────────────────────────────────────────
#
# def init_firebase():
#     if not firebase_admin._apps:
#         if FIREBASE_CREDENTIALS_PATH and FIREBASE_CREDENTIALS_PATH != "placeholder_firebase_path" and os.path.exists(FIREBASE_CREDENTIALS_PATH):
#             try:
#                 cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
#                 firebase_admin.initialize_app(cred)
#             except Exception as e:
#                 logger.error(f"Failed to initialize Firebase: {e}", exc_info=True, extra={"type": "firebase_init_error"})
#         else:
#             logger.info("Firebase credentials not configured. Push notifications will be mocked.", extra={"type": "firebase_init_skip"})
#
# init_firebase()


# ── Public API ──────────────────────────────────────────────────────────────

def send_email_otp(to_email: str, otp: str):
    plain_text = (
        f"Welcome! Your verification code is: {otp}\n\n"
        f"Please enter this code to complete your verification. This code will expire shortly.\n\n"
        f"If you did not request this code, you can safely ignore this email. "
        f"No changes will be made to your account.\n\nThank you."
    )
    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;padding:20px;">
    <h2>Verification Code</h2>
    <p>Welcome! Your verification code is:</p>
    <p style="font-size:24px;font-weight:bold;letter-spacing:4px;padding:12px;text-align:center;">{otp}</p>
    <p>Please enter this code to complete your verification. This code will expire shortly.</p>
    <p>If you did not request this code, you can safely ignore this email. No changes will be made to your account.</p>
    <p>Thank you for using our service.</p>
    <p style="font-size:12px;color:#999;">This is an automated message. Please do not reply to this email.</p>
</body>
</html>'''
    return _send_email(to_email, "Your Verification Code", plain_text, html)

def send_sms_otp(to_phone: str, otp: str):
    return _send_sms(to_phone, f"Your verification code is {otp}")

def generate_otp():
    return str(random.randint(100000, 999999))

def send_reminder_email(to_email: str, member_first_name: str, session_title: str, role: str, session_time: str):
    role_display = role.replace("_", " ").title()
    plain_text = (
        f"Hi {member_first_name},\n\n"
        f"This is a reminder that you are scheduled to serve {ROLE_PREPOSITION} {role_display} "
        f"for the upcoming session: {session_title}.\n\n"
        f"Session: {session_title}\nRole: {role_display}\nTime: {session_time}\n\n"
        f"Please arrive on time and be prepared for your role. "
        f"Thank you for your service and dedication!\n\n"
        f"If you have any questions or need to make changes, please contact your team lead."
    )
    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;padding:20px;">
    <h2>Upcoming Session Reminder</h2>
    <p>Hi {member_first_name},</p>
    <p>This is a reminder that you are scheduled to serve {ROLE_PREPOSITION} <strong>{role_display}</strong>
    for the upcoming session: <strong>{session_title}</strong>.</p>
    <p><strong>Session:</strong> {session_title}<br>
    <strong>Role:</strong> {role_display}<br>
    <strong>Time:</strong> {session_time}</p>
    <p>Please arrive on time and be prepared for your role. Thank you for your service and dedication!</p>
    <p>If you have any questions or need to make changes, please contact your team lead.</p>
    <p style="font-size:12px;color:#999;">This is an automated message. Please do not reply to this email.</p>
</body>
</html>'''
    return _send_email(to_email, "Upcoming Session Reminder", plain_text, html)

def send_reminder_sms(to_phone: str, member_name: str, session_title: str, role: str, session_time: str):
    if not to_phone:
        return False
    body = f"Hi {member_name}, reminder: you are scheduled for {session_title} ({session_time}) {ROLE_PREPOSITION} {role.replace('_', ' ').title()}."
    return _send_sms(to_phone, body)


def send_leader_summary_email(
    to_email: str,
    leader_name: str,
    session_title: str,
    session_time: str,
    assignments: list,       # [{"member_name": str, "role": str}, ...]
    available_members: list,  # [str, ...]  — names
    unavailable_members: list # [str, ...]  — names
):
    """Send a comprehensive session summary email to a leader/admin."""
    # ── Build duty roster rows ──
    duty_rows = ""
    for a in assignments:
        role_display = a["role"].replace("_", " ").title()
        duty_rows += f'''
            <tr>
                <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;font-weight:600;color:#1e293b;">
                    {a["member_name"]}
                </td>
                <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;">
                    <span style="background:#6366f1;color:white;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;">
                        {role_display}
                    </span>
                </td>
            </tr>'''

    if not duty_rows:
        duty_rows = '''
            <tr>
                <td colspan="2" style="padding:14px;text-align:center;color:#94a3b8;font-style:italic;">
                    No assignments yet for this session.
                </td>
            </tr>'''

    # ── Build availability lists ──
    def _member_pills(names, color, icon):
        if not names:
            return f'<p style="color:#94a3b8;font-style:italic;margin:4px 0;">None</p>'
        pills = ""
        for name in sorted(names):
            pills += f'''
                <span style="display:inline-block;background:{color};color:white;padding:4px 12px;
                             border-radius:14px;font-size:13px;font-weight:500;margin:3px 4px;">
                    {icon} {name}
                </span>'''
        return pills

    available_html = _member_pills(available_members, "#16a34a", "✓")
    unavailable_html = _member_pills(unavailable_members, "#dc2626", "✗")

    total = len(available_members) + len(unavailable_members)
    avail_count = len(available_members)
    unavail_count = len(unavailable_members)

    plain_text = (
        f"Session Summary: {session_title}\n"
        f"Time: {session_time}\n\n"
        f"ON DUTY:\n" +
        "\n".join(f"  • {a['member_name']} — {a['role'].replace('_', ' ').title()}" for a in assignments) +
        f"\n\nAVAILABLE ({avail_count}):\n" +
        "\n".join(f"  ✓ {n}" for n in sorted(available_members)) +
        f"\n\nUNAVAILABLE ({unavail_count}):\n" +
        "\n".join(f"  ✗ {n}" for n in sorted(unavailable_members))
    )

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;color:#1e293b;line-height:1.6;padding:0;margin:0;background:#f1f5f9;">
    <div style="max-width:600px;margin:20px auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- Header -->
        <div style="background:#4f46e5;padding:28px 32px;color:white;">
            <h1 style="margin:0;font-size:20px;font-weight:700;letter-spacing:-0.01em;">📋 Session Summary</h1>
            <p style="margin:6px 0 0;font-size:15px;opacity:0.9;">{session_title}</p>
            <p style="margin:4px 0 0;font-size:14px;opacity:0.75;">🕐 {session_time}</p>
        </div>

        <div style="padding:28px 32px;">

            <!-- Greeting -->
            <p style="margin:0 0 6px;font-size:15px;">Hi {leader_name}, here's the overview for the upcoming session:</p>
            <p style="margin:0 0 24px;font-size:18px;font-weight:700;color:#1e293b;">
                {session_title}<br>
                <span style="font-size:14px;font-weight:400;color:#64748b;">{session_time}</span>
            </p>

            <!-- On Duty -->
            <h2 style="margin:0 0 12px;font-size:16px;color:#4f46e5;text-transform:uppercase;letter-spacing:0.06em;font-weight:700;">
                🎤 On Duty
            </h2>
            <table style="width:100%;border-collapse:collapse;margin-bottom:28px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">
                <thead>
                    <tr style="background:#f8fafc;">
                        <th style="padding:10px 14px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:2px solid #e2e8f0;">Member</th>
                        <th style="padding:10px 14px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;border-bottom:2px solid #e2e8f0;">Role</th>
                    </tr>
                </thead>
                <tbody>{duty_rows}
                </tbody>
            </table>

            <!-- Availability -->
            <h2 style="margin:0 0 12px;font-size:16px;color:#4f46e5;text-transform:uppercase;letter-spacing:0.06em;font-weight:700;">
                📊 Team Availability ({avail_count}/{total})
            </h2>

            <!-- Unavailable (shown first and prominently) -->
            <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 16px;margin-bottom:12px;">
                <h3 style="margin:0 0 8px;font-size:13px;color:#dc2626;text-transform:uppercase;letter-spacing:0.05em;font-weight:700;">
                    🔴 Unavailable ({unavail_count})
                </h3>
                {unavailable_html}
            </div>

            <!-- Available -->
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;margin-bottom:20px;">
                <h3 style="margin:0 0 8px;font-size:13px;color:#16a34a;text-transform:uppercase;letter-spacing:0.05em;font-weight:700;">
                    🟢 Available ({avail_count})
                </h3>
                {available_html}
            </div>

        </div>

        <!-- Footer -->
        <div style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">This is an automated leader summary. Please do not reply to this email.</p>
        </div>

    </div>
</body>
</html>'''

    return _send_email(to_email, f"Session Summary: {session_title} — {session_time}", plain_text, html)

def send_push_notification(device_token: str, title: str, body: str):
    """
    Push notifications via FCM — currently disabled (Firebase commented out).
    Logs the notification and returns True as a no-op stub.
    """
    if not device_token:
        return False

    # if not firebase_admin._apps:
    #     logger.debug(f"Mocking PUSH NOTIFICATION to device {device_token} -> {title}: {body}", extra={"type": "push_notification_mock", "device_token": device_token, "title": title})
    #     return True
    #
    # try:
    #     message = messaging.Message(
    #         notification=messaging.Notification(
    #             title=title,
    #             body=body,
    #         ),
    #         token=device_token,
    #     )
    #     response = messaging.send(message)
    #     return True
    # except Exception as e:
    #     logger.error(f"Error sending push notification to {device_token}: {e}", exc_info=True, extra={"type": "push_notification_error", "device_token": device_token, "title": title})
    #     return False

    logger.debug(
        f"Mocking PUSH NOTIFICATION to device {device_token} -> {title}: {body}",
        extra={"type": "push_notification_mock", "device_token": device_token, "title": title},
    )
    return True


def send_availability_reminder_email(
    to_email: str,
    member_first_name: str,
    year: int,
    month: int,
    unavailable_dates: set,
    session_dates: set,
    calendar_url: str,
):
    """
    Send a monthly availability reminder with an HTML calendar grid.

    Args:
        to_email: Formatted email address, e.g. "John Doe <john@example.com>"
        member_first_name: First name for greeting
        year: Target year
        month: Target month (1-12)
        unavailable_dates: Set of ISO date strings the member has marked unavailable
        session_dates: Set of ISO date strings that have scheduled sessions
        calendar_url: Deep-link URL to the calendar page for this month
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

    return _send_email(
        to_email,
        f"📅 {month_name} {year} Availability Reminder — Please Confirm Your Schedule",
        plain_text,
        html,
    )
