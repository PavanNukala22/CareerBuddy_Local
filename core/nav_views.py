"""The ``/go/<key>/`` navigation gateway used by the public landing page.

One view handles every Skill Up / Resources link, so the authentication check
and the post-login redirect behave identically for all of them (desktop menu,
mobile accordion and in-page cards alike).
"""

from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect

from .navigation import destination_for


def nav_go(request, key: str):
    """Resolve a navigation key, enforcing candidate login first.

    Anonymous + protected destination  -> login page with ?next=<destination>
    Authenticated (or public target)   -> straight to the destination

    The destination is built with ``reverse()`` from this server's own URL
    configuration, never from user input, so ``next`` can never point off-site
    (no open redirect) and never back at ``/go/`` itself (no redirect loop).
    """
    destination = destination_for(key)
    if destination is None:
        raise Http404(f"Unknown navigation target: {key}")

    target = destination.path()

    if destination.protected and not request.user.is_authenticated:
        return redirect(f"{settings.LOGIN_URL}?next={quote(target)}")

    return redirect(target)
