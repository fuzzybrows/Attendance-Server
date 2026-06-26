"""Leader/admin session summary email template."""


def _member_pills(names, color, icon):
    """Build HTML pill badges for a list of member names."""
    if not names:
        return '<p style="color:#94a3b8;font-style:italic;margin:4px 0;">None</p>'
    pills = ""
    for name in sorted(names):
        pills += f'''
            <span style="display:inline-block;background:{color};color:white;padding:4px 12px;
                         border-radius:14px;font-size:13px;font-weight:500;margin:3px 4px;">
                {icon} {name}
            </span>'''
    return pills


def leader_summary(
    leader_name: str,
    session_title: str,
    session_time: str,
    assignments: list,
    available_members: list,
    unavailable_members: list,
):
    """
    Return (subject, plain_text, html) for the leader session summary email.

    Args:
        assignments: [{"member_name": str, "role": str}, ...]
        available_members: [str, ...]
        unavailable_members: [str, ...]
    """
    subject = f"Session Summary: {session_title} — {session_time}"

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

    return subject, plain_text, html
