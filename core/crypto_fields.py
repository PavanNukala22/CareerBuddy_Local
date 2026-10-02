"""SR-05 fix: transparent encryption-at-rest for sensitive identity numbers
(Aadhaar / PAN / passport). Values are encrypted with Fernet before hitting
the database and decrypted transparently on read, so calling code (forms,
views, core/mask_utils.py's display-time masking) is unaffected.

The Fernet key is derived from SECRET_KEY rather than a separate env var, to
avoid adding a new required secret to every deployment. Rotating SECRET_KEY
therefore also rotates this key — acceptable here since SECRET_KEY rotation
already invalidates sessions/signed tokens project-wide.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


class EncryptedCharField(models.CharField):
    """A CharField whose value is encrypted at rest. `max_length` governs the
    stored ciphertext, not the plaintext the caller sets — callers should keep
    validating the real plaintext length themselves (as the existing form
    fields already do)."""

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return _get_fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Legacy plaintext row that predates this field, or an
            # already-plaintext value assigned in-memory this request.
            return value
