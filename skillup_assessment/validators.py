"""
Certificate name validation — spec section 3.

Deliberately does NOT restrict to [A-Za-z]: names may legitimately contain
letters from any script (Hindi, Arabic, Vietnamese, etc.), hyphens, and
apostrophes. What it does enforce: non-empty after trimming, a sane maximum
length, no control characters, and no HTML-special characters (defence in
depth against injection when the name is later rendered on a page or
embedded in a PDF/certificate template).
"""
import re
import unicodedata

MAX_CERTIFICATE_NAME_LENGTH = 100

# Any Unicode "letter" category (L*) — matches Latin, Devanagari, Arabic,
# Cyrillic, CJK, etc. Used only to confirm the name isn't purely numbers/
# symbols/whitespace; it does not restrict *which* letters are allowed.
_HAS_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)

# Characters that have no legitimate place in a person's name and are worth
# rejecting outright: HTML/script-injection characters and raw control chars.
_DISALLOWED_CHARS_RE = re.compile(r"[<>{}\\`\x00-\x08\x0b\x0c\x0e-\x1f]")


class CertificateNameError(ValueError):
    """Raised with a user-facing message when a submitted name is invalid."""


def clean_certificate_name(raw_name):
    """Validate and normalize a certificate name.

    Returns the cleaned name on success, or raises CertificateNameError with
    a message safe to show the user.
    """
    if raw_name is None:
        raise CertificateNameError("Please enter your name for the certificate.")

    # Normalize composed/decomposed Unicode forms so equivalent names compare
    # and store consistently across different input methods/keyboards.
    name = unicodedata.normalize("NFC", str(raw_name))

    # Collapse all whitespace runs (including tabs/newlines pasted in) to a
    # single space, then trim the ends — "  Pavan   Nukala  " -> "Pavan Nukala".
    name = re.sub(r"\s+", " ", name).strip()

    if not name:
        raise CertificateNameError("Please enter your name for the certificate.")

    if len(name) > MAX_CERTIFICATE_NAME_LENGTH:
        raise CertificateNameError(
            f"Name is too long (maximum {MAX_CERTIFICATE_NAME_LENGTH} characters)."
        )

    if _DISALLOWED_CHARS_RE.search(name):
        raise CertificateNameError("Name contains characters that aren't allowed.")

    if not _HAS_LETTER_RE.search(name):
        raise CertificateNameError("Please enter a valid name.")

    return name
