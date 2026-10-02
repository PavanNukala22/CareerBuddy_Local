"""Single entry point for sending transactional email over the configured SMTP
backend (ZeptoMail in production — see .env.example / docs/ZeptoMail_SMTP_Setup.pdf).

Every outbound email in this project (welcome emails, employer notifications,
job application confirmations, payment receipts) should call
`send_transactional_email()` instead of building `EmailMultiAlternatives` /
`send_mail` calls by hand, so address validation, header-injection hardening
and failure logging live in one reviewed place rather than being repeated
(and occasionally skipped) at each call site.
"""
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def sanitize_header_value(value):
    """Strip CR/LF from a value bound for an email header.

    Django's SafeMIMEText already rejects a message outright if a header
    contains a raw newline (BadHeaderError), which is safe but turns
    attacker-controlled input — e.g. an employer's own company name reused in
    a From: display name — into a hard failure for that email. Stripping the
    newlines up front keeps one bad field from blocking delivery.
    """
    if not value:
        return value
    return value.replace('\r', ' ').replace('\n', ' ').strip()


def is_valid_email(address):
    if not address:
        return False
    try:
        validate_email(address)
        return True
    except ValidationError:
        return False


def send_transactional_email(subject, to_email, template_name, context, from_email=None, fail_silently=True):
    """Render `template_name` with `context` and email it to `to_email`.

    Returns True once the message is handed off successfully, False on any
    failure (invalid address, template error, SMTP error). Callers here treat
    email as a side effect of something that already succeeded (a signup, a
    payment, a job application) so a dead SMTP connection must never be
    allowed to surface as a user-facing error — set fail_silently=False only
    if the caller has its own handling for that.
    """
    to_email = (to_email or '').strip()
    if not is_valid_email(to_email):
        logger.warning(f"Not sending '{subject}': '{to_email}' is not a valid email address.")
        if not fail_silently:
            raise ValueError(f"Invalid recipient address: {to_email!r}")
        return False

    safe_subject = sanitize_header_value(subject)
    sender = sanitize_header_value(from_email) or settings.DEFAULT_FROM_EMAIL

    try:
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)

        message = EmailMultiAlternatives(
            subject=safe_subject,
            body=text_content,
            from_email=sender,
            to=[to_email],
        )
        message.attach_alternative(html_content, "text/html")
        message.send(fail_silently=False)
        logger.info(f"Email '{safe_subject}' sent to {to_email}.")
        return True
    except Exception as exc:
        logger.error(f"Failed to send email '{safe_subject}' to {to_email}: {exc}")
        if not fail_silently:
            raise
        return False
