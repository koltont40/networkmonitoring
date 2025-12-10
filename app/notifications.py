from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from .settings import settings

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self) -> None:
        self.smtp_enabled = bool(
            settings.smtp_host
            and settings.smtp_username
            and settings.smtp_password
            and settings.smtp_sender
            and settings.smtp_recipients
        )
        self.slack_enabled = bool(settings.slack_webhook_url)

    def _build_email(self, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_sender or "monitor@localhost"
        message["To"] = ", ".join(settings.smtp_recipients)
        message.set_content(body)
        return message

    def send_email(self, subject: str, body: str) -> None:
        if not self.smtp_enabled:
            logger.info("SMTP not configured; skipping email delivery")
            return
        message = self._build_email(subject, body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
                logger.info("Sent email alert: %s", subject)
        except Exception as exc:  # pragma: no cover - operational best effort
            logger.exception("Failed to send email: %s", exc)

    async def send_slack(self, text: str) -> None:
        if not self.slack_enabled:
            logger.info("Slack webhook not configured; skipping notification")
            return
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(settings.slack_webhook_url, json={"text": text})
                resp.raise_for_status()
                logger.info("Sent slack alert")
        except Exception as exc:  # pragma: no cover - operational best effort
            logger.exception("Failed to send slack message: %s", exc)
