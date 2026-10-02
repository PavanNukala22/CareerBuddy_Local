"""Password complexity validator backing the registration checklist UI.

Django's built-in validators cover length, common passwords, numeric-only and
user-attribute similarity, but nothing enforces character variety. The
registration pages advertise uppercase / lowercase / number / special-character
rules to the user, so those rules are enforced here rather than being purely
decorative — otherwise the checklist would tick green for a password the
server happily accepts under different rules.

Kept deliberately in sync with static/js/password-requirements.js, which does
the same checks live in the browser. The server remains the authority; the JS
is only there so the user sees progress as they type.
"""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# Anything that is not a letter, a digit, or whitespace counts as "special".
# Broader than a fixed punctuation list, so symbols people actually reach for
# (currency signs, typographic marks) are accepted rather than silently
# rejected.
SPECIAL_CHAR_RE = re.compile(r'[^A-Za-z0-9\s]')

# Passwords are capped at this length by product decision. Combined with
# Django's MinimumLengthValidator (8) this means passwords are exactly 8
# characters. Note this is a deliberate restriction, not a technical limit —
# a short fixed length materially reduces resistance to offline cracking, so
# raising MAX_PASSWORD_LENGTH (and the matching `maxlength` attributes /
# checklist copy) is the change to make if that trade-off is revisited.
MAX_PASSWORD_LENGTH = 8


class MaximumLengthValidator:
    """Reject passwords longer than MAX_PASSWORD_LENGTH characters."""

    def __init__(self, max_length=MAX_PASSWORD_LENGTH):
        self.max_length = max_length

    def validate(self, password, user=None):
        if len(password) > self.max_length:
            raise ValidationError(
                _('This password is too long. It must contain at most %(max_length)d characters.'),
                code='password_too_long',
                params={'max_length': self.max_length},
            )

    def get_help_text(self):
        return _(
            'Your password must contain at most %(max_length)d characters.'
        ) % {'max_length': self.max_length}


class PasswordComplexityValidator:
    """Require at least one uppercase, lowercase, digit and special character."""

    def validate(self, password, user=None):
        errors = []
        if not re.search(r'[A-Z]', password):
            errors.append(_('at least 1 uppercase letter'))
        if not re.search(r'[a-z]', password):
            errors.append(_('at least 1 lowercase letter'))
        if not re.search(r'[0-9]', password):
            errors.append(_('at least 1 number'))
        if not SPECIAL_CHAR_RE.search(password):
            errors.append(_('at least 1 special character'))

        if errors:
            raise ValidationError(
                _('Password must contain %(missing)s.'),
                code='password_missing_character_types',
                params={'missing': ', '.join(errors)},
            )

    def get_help_text(self):
        return _(
            'Your password must contain at least 1 uppercase letter, '
            '1 lowercase letter, 1 number and 1 special character.'
        )
