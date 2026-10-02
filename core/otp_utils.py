"""Email one-time-password (OTP) helpers for verifying an address at sign-up.

The code and its metadata live in Django's cache (not the database) so they
expire on their own and never accumulate. All state is keyed by the lower-cased
email, so verification cannot be spoofed from the client — a caller proves it
controls the inbox by returning the code we mailed there.
"""
import logging
import secrets

from django.core.cache import cache

from core.email_utils import send_transactional_email, is_valid_email

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 600          # a code is valid for 10 minutes
RESEND_COOLDOWN_SECONDS = 60   # minimum gap between two sends to one address
MAX_VERIFY_ATTEMPTS = 5        # wrong guesses before a code is burned


def _otp_key(email):
    return f'email_otp:{email.strip().lower()}'


def _cooldown_key(email):
    return f'email_otp_cooldown:{email.strip().lower()}'


def generate_and_send_otp(email):
    """Create a 6-digit code, store it, and email it.

    Returns (ok, message). ok is False when the address is invalid or a send was
    requested again within the cooldown window; the message is safe to show the
    user. A failed email send also returns False so the UI does not tell the user
    to check an inbox nothing was sent to.
    """
    email = (email or '').strip()
    if not is_valid_email(email):
        return False, 'Please enter a valid email address first.'

    if cache.get(_cooldown_key(email)):
        return False, 'Please wait a moment before requesting another code.'

    code = f'{secrets.randbelow(1_000_000):06d}'
    cache.set(_otp_key(email), {'code': code, 'attempts': 0}, OTP_TTL_SECONDS)
    cache.set(_cooldown_key(email), True, RESEND_COOLDOWN_SECONDS)

    sent = send_transactional_email(
        subject='Your Career Buddy verification code',
        to_email=email,
        template_name='emails/email_otp.html',
        context={'code': code, 'ttl_minutes': OTP_TTL_SECONDS // 60},
    )
    if not sent:
        # Drop the cooldown so the user can immediately retry a transient failure.
        cache.delete(_cooldown_key(email))
        return False, 'We could not send the code right now. Please try again.'

    logger.info('Email OTP sent to %s', email)
    return True, 'A 6-digit verification code has been sent to your email.'


def verify_otp(email, code):
    """Check a submitted code against the stored one.

    Returns (ok, message). A correct code is single-use (deleted on success).
    Too many wrong guesses burns the code so it cannot be brute-forced within its
    lifetime — the user must request a fresh one.
    """
    email = (email or '').strip()
    code = (code or '').strip()
    record = cache.get(_otp_key(email))
    if not record:
        return False, 'This code has expired. Please request a new one.'

    if record['attempts'] >= MAX_VERIFY_ATTEMPTS:
        cache.delete(_otp_key(email))
        return False, 'Too many incorrect attempts. Please request a new code.'

    if not secrets.compare_digest(str(record['code']), code):
        record['attempts'] += 1
        # Preserve whatever lifetime the code has left rather than resetting it.
        cache.set(_otp_key(email), record, OTP_TTL_SECONDS)
        remaining = MAX_VERIFY_ATTEMPTS - record['attempts']
        return False, f'Incorrect code. {remaining} attempt(s) left.'

    cache.delete(_otp_key(email))
    return True, 'Email verified successfully.'
