import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger(__name__)

def send_verification_code(recipient: str, code: str) -> None:
    """Send through configured SMTP. Development mode deliberately exposes no mail credentials."""
    if not settings.smtp_host:
        log.warning("Development verification code for %s: %s", recipient, code)
        return
    message = EmailMessage()
    message["Subject"] = "Your BRIEFS verification code"
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(f"Your BRIEFS verification code is {code}. It expires in 10 minutes.")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.ehlo()
        # Local mail catchers (Mailpit) serve plain SMTP; real providers always advertise STARTTLS.
        if server.has_extn("starttls"): server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
