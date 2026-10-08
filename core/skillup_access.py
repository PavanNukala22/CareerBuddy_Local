"""Free plan access to Skill Up: English & Vocabulary (incl. grammar) only.

Skill Up lessons are raw static files under static/001 Career Buddy/, served
by WhiteNoise. SkillUpAccessMiddleware sits in front of WhiteNoise and refuses
the lesson pages a Free user may not open, so a locked lesson cannot be
reached by typing its URL either. Paid plans (Normal / Pro) open everything.
"""
from __future__ import annotations

from urllib.parse import unquote

from django.http import HttpResponse

SKILLUP_PREFIX = '/static/001 Career Buddy/'

# Lesson paths (relative to the Skill Up folder) a Free user may open.
FREE_PREFIXES = ('001 CEFR/', 'Vocabulary/', 'GrammerActivities/')
FREE_FILES = {'TechCenter/english_vocab_mock_test.html'}

# Quiz banks (activities.views._QUIZ_SUBJECTS) a Free user may take.
FREE_QUIZ_SUBJECTS = {'english'}


def has_full_skillup(user) -> bool:
    if not (user and user.is_authenticated):
        return False
    from career_app.views import _get_user_plan
    return _get_user_plan(user) in ('normal', 'pro')


def is_free_lesson(rel_path: str) -> bool:
    return rel_path.startswith(FREE_PREFIXES) or rel_path in FREE_FILES


def is_locked_lesson(path: str) -> bool:
    """True for a Skill Up lesson PAGE outside the Free set. Stylesheets,
    scripts and images stay public: locked pages are what holds the content."""
    path = unquote(path)
    if not path.startswith(SKILLUP_PREFIX) or not path.lower().endswith(('.html', '.htm')):
        return False
    rel = path[len(SKILLUP_PREFIX):]
    return rel != 'index.html' and not is_free_lesson(rel)


LOCKED_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Locked — CareerBuddy</title>
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#f4f6fb;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#161c27;padding:24px}
.c{max-width:460px;background:#fff;border-radius:16px;padding:32px;box-shadow:0 10px 30px rgba(20,33,61,.12);text-align:center}
h1{font-size:22px;margin:.4em 0}p{color:#4a5568;line-height:1.6}a{display:inline-block;margin-top:12px;background:#14213D;
color:#fff;text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:700}</style></head>
<body><div class="c"><div style="font-size:40px">&#128274;</div><h1>This Skill Up content is locked</h1>
<p>Your Free plan includes English &amp; Vocabulary, Grammar and one activity. Upgrade to unlock Aptitude,
the Tech Center, the Non-IT Center and certifications.</p>
<a href="/pro/" target="_top">View plans</a></div></body></html>"""


def _session_user(request):
    """The logged-in user, read straight from the session cookie: this
    middleware runs before Session/Auth middleware (it has to beat WhiteNoise)."""
    from django.conf import settings
    from django.contrib.auth import get_user_model, SESSION_KEY
    from importlib import import_module

    key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    if not key:
        return None
    store = import_module(settings.SESSION_ENGINE).SessionStore(key)
    try:
        uid = store.get(SESSION_KEY)
    except Exception:
        return None
    if uid is None:
        return None
    return get_user_model().objects.filter(pk=uid, is_active=True).select_related('profile').first()


class SkillUpAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_locked_lesson(request.path) and not has_full_skillup(_session_user(request)):
            return HttpResponse(LOCKED_PAGE, status=403)
        return self.get_response(request)
