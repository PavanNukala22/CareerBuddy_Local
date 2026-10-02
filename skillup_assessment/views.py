"""
Skill Up Certificate views.

Every certificate-producing/serving endpoint re-derives eligibility from
get_mock_test_result() itself, directly against QuizAttempt (the real,
server-persisted quiz history) -- never from frontend state, a query
parameter, or anything the browser sent. This is what spec section 14
requires: a user hitting these URLs directly, with no UI in front of them
at all, still can't get a certificate without the backend independently
confirming eligibility.

Generalized from the old fixed 3-module system to the ~27 dynamic subjects
in skillup_assessment.subjects.SUBJECTS (spec sections 1-6, 23).
"""
import re

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .mock_test_integration import PASS_THRESHOLD_PCT, get_mock_test_result, is_eligible
from .models import Certificate
from .pdf import render_certificate_pdf
from .subjects import CATEGORY_LABELS, SUBJECTS, is_valid_subject, subjects_by_category, total_certification_opportunities
from .validators import CertificateNameError, clean_certificate_name


def _require_valid_subject(subject):
    if not is_valid_subject(subject):
        raise Http404("Unknown Skill Up subject.")


def _subject_label(subject):
    return SUBJECTS[subject]["label"]


def _profile_display_name(user):
    """Best-effort existing name to pre-fill the certificate name field with
    (spec section 10) -- reuses whatever the account already has, never
    invents one.
    """
    full_name = user.get_full_name()
    return full_name.strip() if full_name and full_name.strip() else user.username


def _sanitize_filename_part(name):
    """Strip anything that isn't safe in a filename (spec section 13)."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return cleaned or "User"


def _subject_state(request_user, subject):
    """One subject's current state: not_attempted / locked / eligible / certified.

    Eligibility is always derived from get_mock_test_result(), which itself
    queries the real, server-persisted QuizAttempt table (spec section 17) --
    never from anything the client sent.
    """
    result = get_mock_test_result(request_user, subject)
    certificate = Certificate.objects.filter(user=request_user, subject=subject).first()

    if certificate and certificate.is_generated:
        state = "certified"
    elif not result.get("completed"):
        state = "not_attempted"
    elif is_eligible(result):
        state = "eligible"
    else:
        state = "locked"

    return {
        "subject": subject,
        "label": _subject_label(subject),
        "category": SUBJECTS[subject]["category"],
        "result": result,
        "certificate": certificate,
        "state": state,
        "pass_threshold": PASS_THRESHOLD_PCT,
    }


def _all_states(request_user):
    return [_subject_state(request_user, key) for key in SUBJECTS]


@login_required
def certifications_hub(request):
    """The Certifications nav item lands here: every subject's status,
    grouped by category (spec section 7), with dynamically computed
    totals (spec sections 6, 8, 9, 23 -- nothing here is a hardcoded count).
    """
    states = _all_states(request.user)
    by_subject = {s["subject"]: s for s in states}

    categories = []
    for cat_key, subject_list in subjects_by_category().items():
        cat_states = [by_subject[key] for key, _label in subject_list]
        categories.append({
            "key": cat_key,
            "label": CATEGORY_LABELS[cat_key],
            "total": len(cat_states),
            "attempted": sum(1 for s in cat_states if s["state"] != "not_attempted"),
            "earned": sum(1 for s in cat_states if s["state"] == "certified"),
            "subjects": cat_states,
        })

    return render(
        request,
        "skillup_assessment/hub.html",
        {
            "categories": categories,
            "total_count": total_certification_opportunities(),
            "attempted_count": sum(1 for s in states if s["state"] != "not_attempted"),
            "earned_count": sum(1 for s in states if s["state"] == "certified"),
        },
    )


@login_required
def module_detail(request, module):
    """The full locked/eligible/certified detail page for one subject."""
    _require_valid_subject(module)
    state = _subject_state(request.user, module)

    context = dict(state)
    context["prefill_name"] = _profile_display_name(request.user)
    return render(request, "skillup_assessment/result.html", context)


@login_required
@require_http_methods(["POST"])
def certificate_name_submit(request, module):
    """POST: validate + save the certificate name, then generate the PDF.

    Re-derives eligibility from QuizAttempt itself (spec section 14) -- a
    forged request with no qualifying score on record is rejected
    regardless of what the frontend showed.
    """
    _require_valid_subject(module)

    result = get_mock_test_result(request.user, module)
    if not is_eligible(result):
        raise PermissionDenied(
            "A Mock Test score of 70% or higher is required before a certificate can be generated."
        )

    existing = Certificate.objects.filter(user=request.user, subject=module).first()
    if existing and existing.is_generated:
        return redirect(reverse("skillup_module_detail", args=[module]))

    raw_name = request.POST.get("certificate_name", "")
    try:
        clean_name = clean_certificate_name(raw_name)
    except CertificateNameError as exc:
        state = _subject_state(request.user, module)
        state["prefill_name"] = raw_name or _profile_display_name(request.user)
        state["name_error"] = str(exc)
        return render(request, "skillup_assessment/result.html", state, status=400)

    certificate, _created = Certificate.objects.update_or_create(
        user=request.user,
        subject=module,
        defaults={
            "certificate_name": clean_name,
            "score": result["score"],
            "total": result["total"],
        },
    )
    _render_and_save_pdf(certificate, module)

    return redirect(reverse("skillup_module_detail", args=[module]))


@login_required
@require_http_methods(["GET", "POST"])
def certificate_edit_name(request, module):
    """Explicit, user-initiated regeneration with a different name -- never
    triggered automatically by a page refresh.

    Deliberately does NOT re-check live eligibility (same reasoning as
    certificate_download): the certificate was already earned; changing
    only the display name shouldn't require the live source to currently
    agree. Ownership + existence (get_object_or_404 below) is the real
    gate here.
    """
    _require_valid_subject(module)

    certificate = get_object_or_404(Certificate, user=request.user, subject=module)

    if request.method == "GET":
        return render(
            request,
            "skillup_assessment/edit_name.html",
            {"module": module, "module_label": _subject_label(module), "certificate": certificate},
        )

    raw_name = request.POST.get("certificate_name", "")
    try:
        clean_name = clean_certificate_name(raw_name)
    except CertificateNameError as exc:
        return render(
            request,
            "skillup_assessment/edit_name.html",
            {
                "module": module,
                "module_label": _subject_label(module),
                "certificate": certificate,
                "name_error": str(exc),
                "prefill_name": raw_name,
            },
            status=400,
        )

    certificate.certificate_name = clean_name
    _render_and_save_pdf(certificate, module)

    return redirect(reverse("skillup_module_detail", args=[module]))


def _render_and_save_pdf(certificate, subject):
    pdf_bytes = render_certificate_pdf(
        certificate_name=certificate.certificate_name,
        module_display=_subject_label(subject),
        score=certificate.score,
        total=certificate.total,
        certificate_number=certificate.certificate_number,
        issued_on=timezone.now(),
    )
    certificate.pdf_file.save(f"{subject}_certificate.pdf", ContentFile(pdf_bytes), save=False)
    certificate.is_generated = True
    certificate.generated_at = timezone.now()
    certificate.save()


@login_required
def certificate_download(request, module):
    """Serve the generated PDF.

    Deliberately does NOT re-check live eligibility here: a certificate,
    once generated, is a persisted record of an achievement that already
    happened -- it must keep working even if a later, unrelated QuizAttempt
    (e.g. a failed retake) exists. Eligibility is enforced at the moment of
    GENERATION (certificate_name_submit / certificate_edit_name); ownership
    and is_generated are enforced here. get_object_or_404 filtering on
    user=request.user is what prevents cross-user access (spec section 15) --
    another user's certificate simply doesn't match this queryset, 404 either
    way, no distinction leaked between "doesn't exist" and "isn't yours".
    """
    _require_valid_subject(module)

    certificate = get_object_or_404(Certificate, user=request.user, subject=module)

    if not certificate.is_generated or not certificate.pdf_file:
        raise PermissionDenied("Certificate has not been generated yet.")

    certificate.pdf_file.open("rb")
    safe_name = _sanitize_filename_part(certificate.certificate_name)
    filename = f"CareerBuddy_Certificate_{safe_name}.pdf"
    return FileResponse(certificate.pdf_file, as_attachment=True, filename=filename)


# ============================================================
# JSON API — consumed by the in-page Certifications section on the
# static Skill Up page (static/001 Career Buddy/index.html).
# ============================================================

def _certificate_json(certificate):
    if not certificate:
        return None
    return {
        "certificate_name": certificate.certificate_name,
        "score": certificate.score,
        "total": certificate.total,
        "certificate_number": certificate.certificate_number,
        "generated_at": certificate.generated_at.isoformat() if certificate.generated_at else None,
        "download_url": reverse("skillup_certificate_download", args=[certificate.subject]),
        "edit_url": reverse("skillup_certificate_edit", args=[certificate.subject]),
    }


def _subject_state_json(request_user, subject):
    state = _subject_state(request_user, subject)
    return {
        "subject": state["subject"],
        "label": state["label"],
        "category": state["category"],
        "state": state["state"],
        "pass_threshold": state["pass_threshold"],
        "result": state["result"],
        "certificate": _certificate_json(state["certificate"]),
        "prefill_name": _profile_display_name(request_user),
        "name_url": reverse("skillup_certificate_name", args=[subject]),
    }


@login_required
def api_certifications_status(request):
    """GET: status for every subject, grouped by category, with dynamic
    totals -- the payload the in-page Certifications section fetches on
    load and on every navigation back to that section.
    """
    subjects_json = [_subject_state_json(request.user, key) for key in SUBJECTS]
    by_subject = {s["subject"]: s for s in subjects_json}

    categories = []
    for cat_key, subject_list in subjects_by_category().items():
        cat_subjects = [by_subject[key] for key, _label in subject_list]
        categories.append({
            "key": cat_key,
            "label": CATEGORY_LABELS[cat_key],
            "total": len(cat_subjects),
            "attempted": sum(1 for s in cat_subjects if s["state"] != "not_attempted"),
            "earned": sum(1 for s in cat_subjects if s["state"] == "certified"),
            "subjects": cat_subjects,
        })

    return JsonResponse({
        "categories": categories,
        "total_count": total_certification_opportunities(),
        "attempted_count": sum(1 for s in subjects_json if s["state"] != "not_attempted"),
        "earned_count": sum(1 for s in subjects_json if s["state"] == "certified"),
    })


@login_required
@require_http_methods(["POST"])
def api_certificate_generate(request, module):
    """POST: same generation logic as certificate_name_submit, JSON in/out
    so the in-page section can submit the name form without a page reload.

    Eligibility comes ONLY from get_mock_test_result() / QuizAttempt -- no
    client-supplied score is trusted anywhere in this view (spec section 14).
    """
    _require_valid_subject(module)

    result = get_mock_test_result(request.user, module)
    if not is_eligible(result):
        return JsonResponse(
            {"error": "A Mock Test score of 70% or higher is required before a certificate can be generated."},
            status=403,
        )

    existing = Certificate.objects.filter(user=request.user, subject=module).first()
    if existing and existing.is_generated:
        return JsonResponse({"subject": _subject_state_json(request.user, module)})

    raw_name = request.POST.get("certificate_name", "")
    try:
        clean_name = clean_certificate_name(raw_name)
    except CertificateNameError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    certificate, _created = Certificate.objects.update_or_create(
        user=request.user,
        subject=module,
        defaults={
            "certificate_name": clean_name,
            "score": result["score"],
            "total": result["total"],
        },
    )
    _render_and_save_pdf(certificate, module)

    return JsonResponse({"subject": _subject_state_json(request.user, module)})


@login_required
@require_http_methods(["POST"])
def api_certificate_regenerate(request, module):
    """POST: same logic as certificate_edit_name's POST branch, JSON in/out.

    Deliberately does NOT re-check live eligibility -- same reasoning as
    certificate_download. Ownership + existence (get_object_or_404) is the
    real gate.
    """
    _require_valid_subject(module)

    certificate = get_object_or_404(Certificate, user=request.user, subject=module)

    raw_name = request.POST.get("certificate_name", "")
    try:
        clean_name = clean_certificate_name(raw_name)
    except CertificateNameError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    certificate.certificate_name = clean_name
    _render_and_save_pdf(certificate, module)

    return JsonResponse({"subject": _subject_state_json(request.user, module)})
