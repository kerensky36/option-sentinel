import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "")

MAX_RETRIES = 3


async def send_alert(subject: str, body: str) -> bool:
    """Send an alert email. Returns True on success."""
    if not all([SMTP_USERNAME, SMTP_PASSWORD, ALERT_RECIPIENT]):
        logger.warning("Email not configured — skipping alert: %s", subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = ALERT_RECIPIENT
    msg.attach(MIMEText(body, "plain"))

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await aiosmtplib.send(
                msg,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USERNAME,
                password=SMTP_PASSWORD,
                start_tls=True,
            )
            logger.info("Alert sent: %s", subject)
            return True
        except Exception as exc:
            logger.warning("Alert send attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)

    logger.error("Alert delivery permanently failed after %d attempts: %s", MAX_RETRIES, subject)
    return False
