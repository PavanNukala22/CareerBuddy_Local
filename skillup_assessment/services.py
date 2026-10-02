"""After-grading bookkeeping for the mock tests (AMCAT, CoCubes, subject quizzes).

Called by the submit endpoints in activities/views.py once a test has been
graded. It is deliberately failure-isolated: the user's score is already
computed by then, so nothing that happens here — saving the attempt,
rendering the certificate PDF — is allowed to turn a graded test into a
"Could not grade the test" error. Failures are logged (logs/errors.log) and
reported back as flags instead.

Certificate rule (unchanged): best attempt >= 70% (PASS_THRESHOLD_PCT).
New: when a logged-in user qualifies and has a full name on their profile,
the certificate is generated straight away, so it is ready to download the
moment the results appear. Without a full name the user is sent to the
existing certificate page to enter the name to print — the name on a
certificate is never guessed from a username.
"""
import logging

from django.db import transaction
from django.urls import reverse

logger = logging.getLogger(__name__)


def record_attempt(user, subject, score, total):
    """Save one graded attempt. Returns True if it was stored."""
    if not getattr(user, "is_authenticated", False) or not total:
        return False
    from .models import QuizAttempt
    try:
        QuizAttempt.objects.create(user=user, subject=subject, score=score, total=total)
        return True
    except Exception:
        logger.exception("Could not save QuizAttempt (user=%s, subject=%s, %s/%s)",
                         getattr(user, "pk", None), subject, score, total)
        return False


def certificate_summary(user, subject, auto_generate=True):
    """Certificate status for one subject, generating it when earned.

    Shape:
        {
          "state": "not_attempted" | "locked" | "eligible" | "certified",
          "pass_threshold": 70,
          "best": {"score", "total", "percentage"} | None,
          "certificate": {..., "download_url", "edit_url"} | None,
          "page_url": "/skill-up/assessment/<subject>/",
          "needs_name": bool,   # eligible, but no profile name to print
        }
    """
    # Imported here: skillup_assessment.subjects imports activities.views,
    # so a module-level import would be circular.
    from .models import Certificate
    from .validators import CertificateNameError, clean_certificate_name
    from .views import _certificate_json, _render_and_save_pdf, _subject_state

    state = _subject_state(user, subject)
    needs_name = False

    if state["state"] == "eligible" and auto_generate:
        full_name = (user.get_full_name() or "").strip()
        clean_name = None
        if full_name:
            try:
                clean_name = clean_certificate_name(full_name)
            except CertificateNameError:
                clean_name = None
        if clean_name:
            result = state["result"]
            try:
                with transaction.atomic():
                    certificate, _ = Certificate.objects.update_or_create(
                        user=user, subject=subject,
                        defaults={"certificate_name": clean_name,
                                  "score": result["score"], "total": result["total"]},
                    )
                    _render_and_save_pdf(certificate, subject)
            except Exception:
                logger.exception("Automatic certificate generation failed (user=%s, subject=%s)",
                                 user.pk, subject)
            state = _subject_state(user, subject)
        else:
            needs_name = True

    result = state["result"] or {}
    best = None
    if result.get("completed") and result.get("total"):
        best = {
            "score": result["score"],
            "total": result["total"],
            "percentage": result["score"] * 100 // result["total"],   # rounded down: 69.9% is not 70%
        }

    certificate = state["certificate"]
    return {
        "state": state["state"],
        "pass_threshold": state["pass_threshold"],
        "best": best,
        "certificate": _certificate_json(certificate) if certificate and certificate.is_generated else None,
        "page_url": reverse("skillup_module_detail", args=[subject]),
        "needs_name": needs_name,
    }


def after_grading(user, subject, score, total):
    """Everything the submit endpoints add to their JSON after grading."""
    authenticated = bool(getattr(user, "is_authenticated", False))
    out = {"authenticated": authenticated, "saved": False, "certificate": None}
    if not authenticated:
        return out
    out["saved"] = record_attempt(user, subject, score, total)
    try:
        out["certificate"] = certificate_summary(user, subject)
    except Exception:
        logger.exception("Could not build certificate status (user=%s, subject=%s)", user.pk, subject)
    return out
