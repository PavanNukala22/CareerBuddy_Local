"""Serve the Skill Up hub through Django so the existing Buddy renders on it.

Nothing about the Skill Up page changes visually: the original markup is passed
straight through. The only difference is that the response is now a Django
template, which means ``includes/aria_assistant.html`` — the one Buddy — is
present on the page, exactly as it is on Activities, Grammar, GD and the rest.
"""

from __future__ import annotations

import os
import re

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.clickjacking import xframe_options_sameorigin

from core.navigation import ALLOWED_SECTIONS

from .skillup_catalog import SKILLUP_DIRNAME, SKILLUP_INDEX, skillup_root

# `</head>` is matched lazily: the document's real one is the first occurrence.
_HEAD_RE = re.compile(r"<head[^>]*>(?P<inner>.*?)</head>", re.S | re.I)

# `</body>` is matched GREEDILY on purpose. Skill Up's error handler builds an
# HTML document inside a JavaScript string literal, so a literal "</body>"
# appears mid-<script> long before the document's own closing tag. A lazy match
# stops there, cutting the injected markup off inside an unterminated <script>
# — the HTML parser then swallows everything that follows, Buddy included, as
# script text. Greedy anchors on the last "</body>", which is the real one.
_BODY_RE = re.compile(r"<body[^>]*>(?P<inner>.*)</body>", re.S | re.I)

# Parse the Skill Up index once and reuse it; re-parse only when the file's
# mtime changes so editing the static page still shows up without a restart.
_PARSE_CACHE: dict = {}


def _parsed_index(index_path: str):
    mtime = os.path.getmtime(index_path)
    cached = _PARSE_CACHE.get(index_path)
    if cached and cached[0] == mtime:
        return cached[1]
    with open(index_path, encoding="utf-8", errors="replace") as handle:
        markup = handle.read()
    head = _HEAD_RE.search(markup)
    body = _BODY_RE.search(markup)
    parsed = (head.group("inner") if head else "",
              body.group("inner") if body else markup)
    _PARSE_CACHE[index_path] = (mtime, parsed)
    return parsed


@login_required
@xframe_options_sameorigin
def skillup_hub(request):
    """Render the Skill Up hub with Buddy attached.

    ``?section=<id>`` scrolls to one of the hub's own sections. The landing
    page sends the section as a query parameter rather than a URL fragment
    because a fragment never reaches the server and so cannot survive the
    ``?next=`` round-trip through the login page. The template turns it back
    into a hash, which is what the hub's own router already listens for.
    Only ids in ALLOWED_SECTIONS are passed through.
    """
    root = skillup_root()
    if not root:
        raise Http404("Skill Up content is not installed.")

    index_path = os.path.join(root, SKILLUP_INDEX)
    if not os.path.isfile(index_path):
        raise Http404("Skill Up index not found.")

    skillup_head, skillup_body = _parsed_index(index_path)

    # `static()` is used rather than a hand-built path so this keeps working
    # under a CDN or a hashed-filename storage backend after collectstatic.
    base_href = static(f"{SKILLUP_DIRNAME}/{SKILLUP_INDEX}").rsplit("/", 1)[0] + "/"

    requested_section = request.GET.get("section", "")
    section = requested_section if requested_section in ALLOWED_SECTIONS else ""

    return render(request, "skillup/skillup_hub.html", {
        "skillup_base": base_href,
        "skillup_head": skillup_head,
        "skillup_body": skillup_body,
        "skillup_section": section,
    })
