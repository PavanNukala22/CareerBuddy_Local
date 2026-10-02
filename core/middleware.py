"""Application-wide content protection.

Adds ``static/js/content-protection.js`` to every full HTML page Django
returns, so copy / paste / print / select-all / text-selection blocking is
enforced on every page without any template having to include it — including
standalone templates that don't extend base.html, error pages, and pages
added in future.

Not touched:
  * Streaming / file responses (downloads, protected media, PDFs).
  * Non-HTML responses (JSON APIs, images, CSS, JS).
  * HTML fragments returned to AJAX calls (no <html>/<head> tag) — a script
    tag there would never run and could upset code that parses the markup.
  * Paths listed in settings.CONTENT_PROTECTION_EXEMPT_PATHS (prefix match).

The Skill Up lesson files under static/001 Career Buddy/ are served as raw
static files and never pass through Django, so each of those carries the
same <script> tag directly.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.templatetags.static import static

MARKER = "data-cb-protect"

# `<head>` or `<head ...>` — but not `<header>`.
_HEAD_OPEN_RE = re.compile(rb"<head(?:\s[^>]*)?>", re.I)
_HTML_OPEN_RE = re.compile(rb"<html(?:\s[^>]*)?>", re.I)

DEFAULT_EXEMPT_PATHS = ("/admin/",)


class ContentProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, "CONTENT_PROTECTION_ENABLED", True)
        self.exempt = tuple(
            getattr(settings, "CONTENT_PROTECTION_EXEMPT_PATHS", DEFAULT_EXEMPT_PATHS)
        )
        self._tag = None

    def _script_tag(self) -> bytes:
        # Built lazily: static() needs the staticfiles app to be ready.
        if self._tag is None:
            src = static("js/content-protection.js")
            self._tag = f'<script src="{src}?v=3" {MARKER}></script>'.encode()
        return self._tag

    def __call__(self, request):
        response = self.get_response(request)

        if not self.enabled or request.path.startswith(self.exempt):
            return response
        if getattr(response, "streaming", False):
            return response
        if not response.get("Content-Type", "").lower().startswith("text/html"):
            return response
        if response.get("Content-Encoding"):
            return response

        content = response.content
        if MARKER.encode() in content:
            return response

        match = _HEAD_OPEN_RE.search(content) or _HTML_OPEN_RE.search(content)
        if not match:
            return response   # an HTML fragment, not a page

        pos = match.end()
        response.content = content[:pos] + self._script_tag() + content[pos:]
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        return response
