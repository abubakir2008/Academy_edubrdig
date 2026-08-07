"""Async SMTP email sender (defaults to the local MailHog catcher)."""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from .core.config import get_settings

_settings = get_settings()
log = logging.getLogger(_settings.service_name)


async def send_email(to: str, subject: str, body: str) -> bool:
    if not _settings.email_enabled or not to:
        return False
    msg = EmailMessage()
    msg["From"] = _settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        await aiosmtplib.send(
            msg,
            hostname=_settings.smtp_host,
            port=_settings.smtp_port,
            username=_settings.smtp_user or None,
            password=_settings.smtp_password or None,
            start_tls=_settings.smtp_tls,
        )
        return True
    except Exception as exc:  # never let email failure break the caller
        log.warning("Email send failed to %s: %s", to, exc)
        return False
