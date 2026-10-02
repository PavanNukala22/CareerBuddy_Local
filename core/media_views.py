"""SR-04 fix: résumés and selfies were served by Django's dev-only static()
helper — reachable by anyone, logged in or not, once the filename is known
(filenames themselves were made non-enumerable separately, in
users/models.py's resume_upload_path()). This adds an authenticated,
ownership-checked view for just these media categories; every other
media path (logos, etc.) keeps going through the normal static() helper.

FileField.url just returns MEDIA_URL + the stored name, so existing template
references like {{ profile.resume.url }} route through this view automatically
once it's mounted at /media/resumes/... and /media/selfies/... — no template
changes needed.

Interview recordings live in the 'interview_videos' storage alias (MinIO in
production, local disk in dev) rather than MEDIA_ROOT, so they are read
through that storage instead of the filesystem.
"""
import mimetypes
import os
import re

from django.conf import settings
from django.core.files.storage import storages
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET


def _can_access_media(user, category, relative_path):
    if user.is_staff or user.is_superuser:
        return True

    employer_profile = getattr(user, 'employer_profile', None)

    if category == 'interview_videos':
        from career_app.models import ResumeInterviewSession
        # The candidate who took the interview...
        if ResumeInterviewSession.objects.filter(
            resume__user=user, interview_video=relative_path
        ).exists():
            return True
        # ...or an employer that candidate has applied to. Only passing
        # sessions ever have a recording, so no score check is needed here.
        if employer_profile:
            # Case 1: candidate applied directly to one of the employer's own jobs.
            if ResumeInterviewSession.objects.filter(
                interview_video=relative_path,
                resume__user__job_applications__job__employer=employer_profile,
            ).exists():
                return True
            # Case 2: resume-parsed applications (source='resume_parsed') are
            # attributed to system-seeded jobs not owned by any employer, so the
            # job__employer lookup above won't match. Instead, check whether the
            # candidate has a resume-parsed application that the employer can see
            # in their all_applications view (which includes resume_parsed source).
            from jobs_app.models import JobApplication
            if ResumeInterviewSession.objects.filter(
                interview_video=relative_path,
                resume__user__job_applications__source='resume_parsed',
            ).exists():
                return True
        return False

    from users.models import UserProfile
    own_field = 'selfie' if category == 'selfies' else 'resume'
    if UserProfile.objects.filter(user=user, **{own_field: relative_path}).exists():
        return True

    from jobs_app.models import JobApplication

    if category == 'resumes':
        # The candidate who applied with this résumé copy...
        if JobApplication.objects.filter(applicant_user=user, resume=relative_path).exists():
            return True
        # ...or the employer whose job posting that application was made to.
        if employer_profile and JobApplication.objects.filter(
            job__employer=employer_profile, resume=relative_path
        ).exists():
            return True
    elif category == 'selfies':
        # An employer may view the selfie of a candidate who applied to one of their jobs.
        if employer_profile and JobApplication.objects.filter(
            job__employer=employer_profile, applicant_user__profile__selfie=relative_path
        ).exists():
            return True

    return False


def _parse_byte_range(range_header, size):
    """(start, end) for a single `Range: bytes=...` header, or None.

    Only the single-range form is handled — that is all a browser's media
    element ever sends. Anything malformed, multi-range or unsatisfiable
    returns None and the caller answers with the whole file, which is a legal
    response to any Range request.
    """
    if not range_header or size <= 0:
        return None
    match = re.match(r'^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*$', str(range_header))
    if not match:
        return None
    raw_start, raw_end = match.group(1), match.group(2)

    if raw_start == '':
        if raw_end == '':
            return None
        # "bytes=-500" — the LAST 500 bytes.
        length = min(int(raw_end), size)
        if length <= 0:
            return None
        return size - length, size - 1

    start = int(raw_start)
    end = int(raw_end) if raw_end else size - 1
    end = min(end, size - 1)
    if start > end or start >= size:
        return None
    return start, end


def _serve_interview_video(relative_path, request=None):
    """Stream one recording, honouring HTTP Range.

    Chrome and Edge ask for `Range: bytes=0-` before they will play a video at
    all, and send a fresh range every time the user drags the scrubber. A plain
    200 with the whole body makes the clip unseekable (and, for some
    containers, unplayable), so a range request is answered with 206 and the
    requested slice.
    """
    storage = storages['interview_videos']
    if not storage.exists(relative_path):
        raise Http404

    content_type = mimetypes.guess_type(relative_path)[0] or 'video/webm'
    try:
        size = storage.size(relative_path)
    except Exception:
        size = 0

    byte_range = _parse_byte_range(
        request.headers.get('Range') if request is not None else None, size
    )

    if byte_range is None:
        response = FileResponse(storage.open(relative_path, 'rb'), content_type=content_type)
        if size:
            response['Content-Length'] = str(size)
        response['Accept-Ranges'] = 'bytes'
        return response

    start, end = byte_range
    length = end - start + 1
    handle = storage.open(relative_path, 'rb')
    handle.seek(start)

    def chunks(remaining, block=64 * 1024):
        try:
            while remaining > 0:
                data = handle.read(min(block, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data
        finally:
            handle.close()

    response = StreamingHttpResponse(chunks(length), status=206, content_type=content_type)
    response['Content-Range'] = f'bytes {start}-{end}/{size}'
    response['Content-Length'] = str(length)
    response['Accept-Ranges'] = 'bytes'
    return response


@login_required
@require_GET
def serve_protected_media(request, category, filename):
    if category not in ('resumes', 'selfies', 'interview_videos'):
        raise Http404
    relative_path = f'{category}/{filename}'
    if not _can_access_media(request.user, category, relative_path):
        raise Http404

    if category == 'interview_videos':
        return _serve_interview_video(relative_path, request)

    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    full_path = os.path.abspath(full_path)
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    # Refuse anything that resolves outside MEDIA_ROOT (path traversal).
    if not full_path.startswith(media_root + os.sep) or not os.path.isfile(full_path):
        raise Http404

    return FileResponse(open(full_path, 'rb'))
