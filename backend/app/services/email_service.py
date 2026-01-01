from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from collections.abc import Iterable, Sequence
from email.message import EmailMessage

from app.config import get_settings
from app.core.settings import Settings

logger = logging.getLogger(__name__)


def build_frontend_url(path: str, settings: Settings | None = None) -> str:
    """Join the configured frontend base URL with a path."""
    settings = settings or get_settings()
    base = (settings.frontend_url or "").rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    return f"{base}{normalized_path}"


def _normalize_recipients(to: str | Sequence[str]) -> list[str]:
    recipients: Iterable[str] = [to] if isinstance(to, str) else to
    cleaned = [str(recipient).strip() for recipient in recipients if str(recipient).strip()]
    if not cleaned:
        raise ValueError("Recipient list is empty")
    return cleaned


def _build_message(
    *,
    settings: Settings,
    to: str | Sequence[str],
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> EmailMessage:
    sender = settings.email_from or settings.email_user
    if not settings.email_host or not sender:
        raise RuntimeError("Email configuration is missing EMAIL_HOST and EMAIL_FROM/EMAIL_USER")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(_normalize_recipients(to))
    message["Subject"] = subject
    message.set_content(body_text)
    if body_html:
        message.add_alternative(body_html, subtype="html")
    return message


def _send_sync(message: EmailMessage, settings: Settings) -> None:
    if settings.email_ssl and settings.email_tls:
        raise RuntimeError("EMAIL_SSL and EMAIL_TLS cannot both be enabled")
    use_ssl = bool(settings.email_ssl)
    context = ssl.create_default_context()
    if not settings.email_host or settings.email_port is None:
        raise RuntimeError("Email configuration is missing EMAIL_HOST/EMAIL_PORT")
    host = settings.email_host
    port = settings.email_port

    if use_ssl:
        client: smtplib.SMTP | smtplib.SMTP_SSL = smtplib.SMTP_SSL(
            host,
            port,
            context=context,
        )
    else:
        client = smtplib.SMTP(host, port)

    with client as smtp:
        if not use_ssl and settings.email_tls:
            smtp.starttls(context=context)
        if settings.email_user:
            smtp.login(settings.email_user, settings.email_password or "")
        smtp.send_message(message)


async def send_email(
    to: str | Sequence[str],
    subject: str,
    body_text: str,
    body_html: str | None = None,
    settings: Settings | None = None,
) -> None:
    """
    Send an email using the configured SMTP credentials.

    This runs the blocking SMTP call in a thread to avoid stalling the event loop.
    """
    settings = settings or get_settings()
    message = _build_message(settings=settings, to=to, subject=subject, body_text=body_text, body_html=body_html)
    logger.info("Sending email to %s via %s:%s", message["To"], settings.email_host, settings.email_port)
    await asyncio.to_thread(_send_sync, message, settings)

async def send_portal_link_email(
    *,
    to_email: str,
    portal_url: str,
    settings: Settings | None = None,
    audience: str | None = None,
    display_name: str | None = None,
) -> None:
    """
    Send a portal link email; audience is a hint like 'customer' or 'supplier'.
    """
    settings = settings or get_settings()
    audience_label = (audience or "portal").title()
    subject = f"{settings.app_name} {audience_label} portal link"
    greeting = f"Hi {display_name}," if display_name else "Hello,"
    body_text = f"""{greeting}

Access your portal here: {portal_url}

If you did not request this link, you can ignore this email."""
    body_html = f"""
        <p>{greeting}</p>
        <p>Access your portal here:</p>
        <p><a href="{portal_url}">{portal_url}</a></p>
        <p>If you did not request this link, you can ignore this email.</p>
    """
    await send_email(
        to=to_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        settings=settings,
    )


__all__ = ["send_email", "build_frontend_url", "send_portal_link_email"]
