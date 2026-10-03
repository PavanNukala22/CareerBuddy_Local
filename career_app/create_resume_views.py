"""Endpoints for the Create Resume builder on the landing page.

Preview, PDF and page images work for every visitor (like the builder
itself); saved drafts need a signed-in user and every draft query is filtered
by ``request.user``, so one candidate can never read, change or delete
another's resume. All POSTs are CSRF-protected, size-limited and rate-limited
per IP. Submitted resume text is never logged.
"""
import base64
import json
import logging

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .create_resume import build_document, draft_title, normalize, resume_filename, section_status, validate
from .models import ResumeDraft

logger = logging.getLogger(__name__)

MAX_PAYLOAD_BYTES = 300_000
# The live preview posts on every pause in typing, so it gets a far larger
# allowance than the PDF / page-image endpoints that do real rendering work.
LIMITS = {'preview': (900, 600), 'render': (120, 600), 'drafts': (300, 600)}


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return xff.split(',')[0].strip() if xff else (request.META.get('REMOTE_ADDR', '') or 'unknown')


def _limited(request, bucket):
    limit, window = LIMITS[bucket]
    key = f'create_resume:{bucket}:{_client_ip(request)}'
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window)
        count = 1
    return count > limit


def _too_many():
    return JsonResponse({'ok': False, 'errors': [{'field': '', 'section': '',
                         'message': 'Too many requests. Please wait a few minutes and try again.'}]}, status=429)


def _bad(message='The resume data could not be read.', status=400):
    return JsonResponse({'ok': False, 'errors': [{'field': '', 'section': '', 'message': message}]}, status=status)


def _read(request):
    body = request.body if request.content_type == 'application/json' else (request.POST.get('payload') or '').encode()
    if not body or len(body) > MAX_PAYLOAD_BYTES:
        return None
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None


@require_POST
def preview_api(request):
    """Live preview: the document is returned even while required fields are missing."""
    if _limited(request, 'preview'):
        return _too_many()
    raw = _read(request)
    if raw is None:
        return _bad()
    state = normalize(raw)
    errors = validate(state)
    return JsonResponse({'ok': True, 'document': build_document(state), 'errors': errors,
                         'status': section_status(state, errors), 'filename': resume_filename(state)})


def _ready_state(request):
    if _limited(request, 'render'):
        return None, _too_many()
    raw = _read(request)
    if raw is None:
        return None, _bad()
    state = normalize(raw)
    errors = validate(state)
    if errors:
        return None, JsonResponse({'ok': False, 'errors': errors}, status=400)
    return state, None


@require_POST
def pdf_download(request):
    """The resume as a real PDF; ``inline=1`` opens it in the browser (print preview / print)."""
    state, error = _ready_state(request)
    if error:
        if request.content_type != 'application/json':
            text = '\n'.join(e['message'] for e in json.loads(error.content).get('errors', []))
            return HttpResponse(text or 'The resume could not be generated.', status=error.status_code,
                                content_type='text/plain; charset=utf-8')
        return error
    try:
        from .create_resume_pdf import render_pdf
        pdf = render_pdf(build_document(state))
    except Exception:
        logger.exception('Create Resume PDF generation failed')
        return _bad('The PDF could not be generated. Please try again.', 500)
    filename = resume_filename(state)
    inline = request.GET.get('inline') == '1' or request.POST.get('inline') == '1'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'{"inline" if inline else "attachment"}; filename="{filename}"'
    response['X-Resume-Filename'] = filename
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def pages_api(request):
    """Print preview: page images rendered from the actual PDF."""
    state, error = _ready_state(request)
    if error:
        return error
    try:
        from .create_resume_pdf import render_page_images, render_pdf
        images, total = render_page_images(render_pdf(build_document(state)), scale=1.4, max_pages=10)
    except Exception:
        logger.exception('Create Resume page preview failed')
        return _bad('Print preview is unavailable. Use Download PDF to view the pages.', 500)
    return JsonResponse({'ok': True, 'total': total,
                         'pages': ['data:image/png;base64,' + base64.b64encode(i).decode() for i in images]})


# --------------------------------------------------------------------------- #
#  Saved drafts (signed-in candidates only, always scoped to request.user)
# --------------------------------------------------------------------------- #

def _summary(draft):
    return {'id': draft.id, 'title': draft.title, 'template': draft.template,
            'updated': draft.updated_at.isoformat()}


def _json_login_required(view):
    """login_required that answers AJAX callers with 401 JSON instead of a redirect."""
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'ok': False, 'errors': [{'field': '', 'section': '',
                                 'message': 'Please sign in to save resumes to your account.'}]}, status=401)
        if _limited(request, 'drafts'):
            return _too_many()
        return view(request, *args, **kwargs)
    wrapped.__name__ = view.__name__
    wrapped.__doc__ = view.__doc__
    return wrapped


@require_GET
@_json_login_required
def drafts_list(request):
    drafts = ResumeDraft.objects.filter(user=request.user)
    return JsonResponse({'ok': True, 'drafts': [_summary(d) for d in drafts]})


@require_GET
@_json_login_required
def draft_detail(request, pk):
    draft = get_object_or_404(ResumeDraft, pk=pk, user=request.user)
    return JsonResponse({'ok': True, 'draft': _summary(draft), 'data': draft.data})


@require_POST
@_json_login_required
def draft_save(request):
    """Create (no id) or update (own id) a draft. Partial resumes may be saved."""
    raw = _read(request)
    if not isinstance(raw, dict):
        return _bad()
    state = normalize(raw.get('data'))
    draft_id = raw.get('id')
    if draft_id:
        draft = get_object_or_404(ResumeDraft, pk=draft_id, user=request.user)
    else:
        if ResumeDraft.objects.filter(user=request.user).count() >= ResumeDraft.MAX_PER_USER:
            return _bad(f'You can keep up to {ResumeDraft.MAX_PER_USER} resumes. Delete one to save a new resume.')
        draft = ResumeDraft(user=request.user)
    draft.data = state
    draft.template = state['template']
    draft.title = draft_title(state)
    draft.save()
    return JsonResponse({'ok': True, 'draft': _summary(draft)})


@require_POST
@_json_login_required
def draft_delete(request, pk):
    get_object_or_404(ResumeDraft, pk=pk, user=request.user).delete()
    return JsonResponse({'ok': True})
