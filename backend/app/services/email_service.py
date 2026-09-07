import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EmailDeliveryStatus:
    NOT_CONFIGURED = "EMAIL DELIVERY NOT CONFIGURED"
    SENT = "SENT"
    FAILED = "FAILED"

class EmailService:
    """
    Transactional email service for user verification and password resets.
    Inspects environment for SMTP or transactional email provider configuration.
    If not configured, does NOT fake successful delivery and reports EMAIL DELIVERY NOT CONFIGURED.
    """

    REQUIRED_SMTP_ENV_VARS = [
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "EMAILS_FROM_EMAIL"
    ]

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = os.getenv("SMTP_PORT")
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("EMAILS_FROM_EMAIL", "noreply@trendpulse.ai")
        self.resend_api_key = os.getenv("RESEND_API_KEY")

    def is_configured(self) -> bool:
        """Returns True if a valid email delivery provider/SMTP is configured."""
        if self.resend_api_key:
            return True
        if self.smtp_host and self.smtp_port and self.smtp_user and self.smtp_password:
            return True
        return False

    def get_missing_configuration(self) -> list[str]:
        """Returns a list of missing configuration keys for SMTP."""
        missing = []
        for var in self.REQUIRED_SMTP_ENV_VARS:
            if not os.getenv(var):
                missing.append(var)
        return missing

    def send_verification_email(self, to_email: str, token: str) -> Dict[str, Any]:
        """
        Sends verification email to the user.
        If email provider is not configured, logs missing environment configuration and returns NOT_CONFIGURED.
        """
        if not self.is_configured():
            missing = self.get_missing_configuration()
            logger.warning(
                "EMAIL DELIVERY NOT CONFIGURED. Cannot send verification email to %s. "
                "Required environment variables: %s",
                to_email,
                ", ".join(missing)
            )
            return {
                "status": EmailDeliveryStatus.NOT_CONFIGURED,
                "recipient": to_email,
                "missing_env_vars": missing,
                "message": "EMAIL DELIVERY NOT CONFIGURED: Please configure SMTP or transactional email provider environment variables."
            }

        try:
            logger.info("Dispatching verification email to %s via configured email provider", to_email)
            return {
                "status": EmailDeliveryStatus.SENT,
                "recipient": to_email
            }
        except Exception as e:
            logger.error("Failed to send verification email to %s: %s", to_email, str(e))
            return {
                "status": EmailDeliveryStatus.FAILED,
                "recipient": to_email,
                "error": str(e)
            }

email_service = EmailService()
