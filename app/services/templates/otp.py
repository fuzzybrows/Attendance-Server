"""OTP verification email and SMS templates."""


def email_otp(otp: str):
    """Return (subject, plain_text, html) for the email OTP verification."""
    subject = "Your Verification Code"

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

    return subject, plain_text, html


def sms_otp(otp: str):
    """Return the SMS body for OTP verification."""
    return f"Your verification code is {otp}"
