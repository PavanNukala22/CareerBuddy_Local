"""Shared masking for sensitive identification numbers (Aadhaar/PAN/Passport).

Kept as plain functions (not template-filter-only) so both the Django
template filters below and static/js/mask-reveal.js's client-side masking
(used for pre-filled edit-form inputs — see templates/includes/mask_reveal_field.html)
implement the exact same rule and never drift apart.
"""

# Last N characters shown in the clear; everything before that is replaced
# with X. Aadhaar is additionally grouped in 4s (its conventional printed
# format), matching the "XXXX XXXX 1234" example.
VISIBLE_CHARS = 4


def _mask_last_n(value, visible=VISIBLE_CHARS):
    value = (value or '').strip()
    if not value:
        return ''
    if len(value) <= visible:
        return 'X' * len(value)
    return ('X' * (len(value) - visible)) + value[-visible:]


def mask_aadhar(value):
    """"547386879801" -> "XXXX XXXX 9801" """
    masked = _mask_last_n(value)
    if not masked:
        return ''
    groups = [masked[i:i + 4] for i in range(0, len(masked), 4)]
    return ' '.join(groups)


def mask_pan(value):
    """"ABCDE1234F" -> "XXXXXX234F" """
    return _mask_last_n(value)


def mask_passport(value):
    """"A1234567" -> "XXXX4567" """
    return _mask_last_n(value)
