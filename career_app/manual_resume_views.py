"""Endpoints for the manual (rule-based, no-AI) Resume Builder on the landing page.

The builder is open to visitors exactly like the role cards it lives in, so
these views do not require a login. They are CSRF-protected, size-limited and
rate-limited per IP, and nothing the candidate submits is stored or logged:
each request turns the posted form state into a preview document or a PDF and
returns it.
"""
import base64
import json
import logging

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .resume_document import (build_document, completeness, normalize_state, resume_filename,
                              validate_state, warnings_for)
from .resume_roles import CUSTOM_PREFIX, client_payload, custom_role, get_role

logger = logging.getLogger(__name__)

MAX_PAYLOAD_BYTES = 200_000
RATE_LIMIT = 60          # requests …
RATE_WINDOW = 10 * 60    # … per IP per 10 minutes


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def _rate_limited(request):
    key = f'manual_resume:{_client_ip(request)}'
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, RATE_WINDOW)
        count = 1
    return count > RATE_LIMIT


def _read_state(request):
    """The builder posts JSON; the Print button posts a form field named 'payload'."""
    if request.content_type == 'application/json':
        body = request.body
    else:
        body = (request.POST.get('payload') or '').encode()
    if not body or len(body) > MAX_PAYLOAD_BYTES:
        return None
    try:
        return normalize_state(json.loads(body))
    except (ValueError, UnicodeDecodeError):
        return None


def _role_for(state):
    """The predefined role, or the generic one described by the posted ``role_def``."""
    role = get_role(state['role'])
    if role is None and state['role'].startswith(CUSTOM_PREFIX):
        role = custom_role(state.get('role_def'))
    return role


def _prepare(request):
    """Shared request handling → (state, role, errors) or an error response."""
    if _rate_limited(request):
        return None, None, JsonResponse(
            {'ok': False, 'errors': [{'field': '', 'step': 0,
                                      'message': 'Too many requests. Please wait a few minutes and try again.'}]},
            status=429)
    state = _read_state(request)
    if state is None:
        return None, None, JsonResponse(
            {'ok': False, 'errors': [{'field': '', 'step': 0, 'message': 'The resume data could not be read.'}]},
            status=400)
    role = _role_for(state)
    errors = validate_state(state, role)
    if errors:
        return state, role, JsonResponse({'ok': False, 'errors': errors,
                                          'completeness': completeness(state, role)}, status=400)
    return state, role, None


@require_GET
def roles_api(request):
    """Predefined role and experience data.

    ``?slug=<role>`` returns that role's full data (form fields, experience-level
    suggestions, summary templates); ``?spec=<json>`` returns a generic role for
    a career-path card with no template (see ``custom_role``); without either,
    every role in full.
    """
    spec = request.GET.get('spec')
    if spec:
        try:
            role = custom_role(json.loads(spec[:20_000]))
        except ValueError:
            role = None
        if role is None:
            return JsonResponse({'ok': False, 'error': 'Unknown role.'}, status=404)
        return JsonResponse({'ok': True, 'role': role})
    slug = request.GET.get('slug')
    if slug:
        role = get_role(slug)
        if role is None:
            return JsonResponse({'ok': False, 'error': 'Unknown role.'}, status=404)
        return JsonResponse({'ok': True, 'role': role})
    return JsonResponse(client_payload(full=True))


@require_POST
def preview_api(request):
    state, role, error = _prepare(request)
    if error:
        return error
    return JsonResponse({
        'ok': True,
        'document': build_document(state, role),
        'warnings': warnings_for(state, role),
        'completeness': completeness(state, role),
        'filename': resume_filename(state, role),
    })


def _pdf_bytes(state, role):
    from .resume_pdf import render_pdf
    return render_pdf(build_document(state, role))


@require_POST
def pdf_download(request):
    """The resume as a real PDF. ``inline=1`` opens it in the browser for printing."""
    state, role, error = _prepare(request)
    if error:
        if request.content_type != 'application/json':
            # The Print button opens a new tab; show the reason there in plain text.
            data = json.loads(error.content)
            text = '\n'.join(e['message'] for e in data.get('errors', []))
            return HttpResponse(text or 'The resume could not be generated.', status=error.status_code,
                                content_type='text/plain; charset=utf-8')
        return error
    try:
        pdf = _pdf_bytes(state, role)
    except Exception:
        logger.exception('Manual resume PDF generation failed')
        return JsonResponse({'ok': False, 'errors': [{'field': '', 'step': 0,
                             'message': 'The PDF could not be generated. Please try again.'}]}, status=500)
    filename = resume_filename(state, role)
    inline = request.GET.get('inline') == '1' or request.POST.get('inline') == '1'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'{"inline" if inline else "attachment"}; filename="{filename}"'
    response['X-Resume-Filename'] = filename
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def preview_pages_api(request):
    """Page-by-page images rendered from the actual PDF, so the preview matches the download."""
    state, role, error = _prepare(request)
    if error:
        return error
    try:
        from .resume_pdf import render_page_images
        images, total = render_page_images(_pdf_bytes(state, role))
    except Exception:
        logger.exception('Manual resume page preview failed')
        return JsonResponse({'ok': False, 'errors': [{'field': '', 'step': 0,
                             'message': 'Page preview is unavailable. Use Download PDF to view the pages.'}]},
                            status=500)
    return JsonResponse({
        'ok': True,
        'total': total,
        'pages': ['data:image/png;base64,' + base64.b64encode(img).decode() for img in images],
        'filename': resume_filename(state, role),
    })
