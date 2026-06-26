"""Session reminder email and SMS templates."""


def reminder_email(member_first_name: str, session_title: str, role_display: str, session_time: str, role_preposition: str):
    """Return (subject, plain_text, html) for the session reminder email."""
    subject = "Upcoming Session Reminder"

    plain_text = (
        f"Hi {member_first_name},\n\n"
        f"This is a reminder that you are scheduled to serve {role_preposition} {role_display} "
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
    <p>This is a reminder that you are scheduled to serve {role_preposition} <strong>{role_display}</strong>
    for the upcoming session: <strong>{session_title}</strong>.</p>
    <p><strong>Session:</strong> {session_title}<br>
    <strong>Role:</strong> {role_display}<br>
    <strong>Time:</strong> {session_time}</p>
    <p>Please arrive on time and be prepared for your role. Thank you for your service and dedication!</p>
    <p>If you have any questions or need to make changes, please contact your team lead.</p>
    <p style="font-size:12px;color:#999;">This is an automated message. Please do not reply to this email.</p>
</body>
</html>'''

    return subject, plain_text, html


def reminder_sms(member_name: str, session_title: str, role_display: str, session_time: str, role_preposition: str):
    """Return the SMS body for the session reminder."""
    return f"Hi {member_name}, reminder: you are scheduled for {session_title} ({session_time}) {role_preposition} {role_display}."
