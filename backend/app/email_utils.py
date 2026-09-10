"""Password-reset OTP delivery through the configured SMTP server."""

import logging
import smtplib
from email.message import EmailMessage

from .config import settings
from .models import User

logger = logging.getLogger(__name__)


def send_password_reset_email(user: User, otp: str) -> bool:
    """Send a six-digit OTP. Return False when SMTP is not configured."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.error("SMTP not configured; reset email cannot be sent to %s", user.email)
        return False

    message = EmailMessage()
    message["Subject"] = "KRISS SMS Shield - Password Reset Code"
    message["From"] = settings.smtp_from
    message["To"] = user.email
    message.set_content(
        f"Hi {user.name},\n\nYour password reset code is: {otp}\n\n"
        f"This code expires in {settings.password_reset_token_minutes} minutes.\n"
        "If you did not request this, ignore this email."
    )
    message.add_alternative(
        f"""<html><body style="font-family:Arial,sans-serif;color:#111827">
        <h2 style="color:#075AA6">KRISS SMS Shield</h2><p>Hi {user.name},</p>
        <p>Use this verification code to reset your password:</p>
        <p style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#075AA6">{otp}</p>
        <p>This code expires in {settings.password_reset_token_minutes} minutes.</p>
        <p>If you did not request this, ignore this email.</p></body></html>""",
        subtype="html",
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)
    return True
