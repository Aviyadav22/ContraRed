"""
Transactional email service using Resend.

Handles password reset emails, dunning notifications, and other transactional emails.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_resend_available = False
try:
    import resend
    _resend_available = True
except ImportError:
    logger.warning("resend package not installed — email features disabled")


def _ensure_configured() -> bool:
    """Return True if Resend is configured and available."""
    if not _resend_available:
        logger.error("Cannot send email: resend package not installed")
        return False
    if not settings.RESEND_API_KEY:
        logger.error("Cannot send email: RESEND_API_KEY not set")
        return False
    resend.api_key = settings.RESEND_API_KEY
    return True


async def send_password_reset_email(to: str, token: str) -> bool:
    """Send a password reset email with a time-limited link.

    Returns True if the email was sent successfully, False otherwise.
    """
    if not _ensure_configured():
        return False

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #1a1a1a; margin-bottom: 24px;">Reset Your Password</h2>
        <p style="color: #4a4a4a; line-height: 1.6;">
            You requested a password reset for your ContraRed account. Click the button below to set a new password.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{reset_url}"
               style="background-color: #dc2626; color: white; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">
                Reset Password
            </a>
        </div>
        <p style="color: #6b6b6b; font-size: 14px; line-height: 1.6;">
            This link expires in 1 hour. If you didn't request this, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #e5e5e5; margin: 24px 0;" />
        <p style="color: #9a9a9a; font-size: 12px;">
            ContraRed — AI-Powered Contract Redlining
        </p>
    </div>
    """

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": "Reset Your ContraRed Password",
            "html": html_body,
        }))
        logger.info("Password reset email sent to %s", to[:3] + "***")
        return True
    except Exception as exc:
        logger.error("Failed to send password reset email: %s", exc)
        return False


async def send_dunning_email(
    user_email: str,
    user_name: str,
    plan: str,
    attempts: int,
    next_retry_at: Optional[datetime] = None,
) -> bool:
    """Send a payment failure notification email.

    Returns True if sent successfully, False otherwise.
    """
    if not _ensure_configured():
        return False

    retry_info = ""
    if next_retry_at:
        retry_info = f"We'll retry your payment on {next_retry_at.strftime('%B %d, %Y')}."
    else:
        retry_info = "Your account has been downgraded to the Free plan due to repeated payment failures."

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #dc2626; margin-bottom: 24px;">Payment Failed</h2>
        <p style="color: #4a4a4a; line-height: 1.6;">
            Hi {user_name},
        </p>
        <p style="color: #4a4a4a; line-height: 1.6;">
            We were unable to process your payment for the ContraRed <strong>{plan.title()}</strong> plan.
            This is attempt {attempts} of 4.
        </p>
        <p style="color: #4a4a4a; line-height: 1.6;">
            {retry_info}
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{settings.FRONTEND_URL}/settings/billing"
               style="background-color: #dc2626; color: white; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">
                Update Payment Method
            </a>
        </div>
        <p style="color: #6b6b6b; font-size: 14px; line-height: 1.6;">
            If you believe this is an error, please contact support.
        </p>
        <hr style="border: none; border-top: 1px solid #e5e5e5; margin: 24px 0;" />
        <p style="color: #9a9a9a; font-size: 12px;">
            ContraRed — AI-Powered Contract Redlining
        </p>
    </div>
    """

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [user_email],
            "subject": f"Action Required: Payment Failed for ContraRed {plan.title()} Plan",
            "html": html_body,
        }))
        logger.info("Dunning email sent to %s (attempt %d)", user_email[:3] + "***", attempts)
        return True
    except Exception as exc:
        logger.error("Failed to send dunning email: %s", exc)
        return False
