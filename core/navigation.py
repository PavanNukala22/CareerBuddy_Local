"""Centralised navigation map for the public landing page.

Every Skill Up / Resources link on the landing page points at the ``nav_go``
gateway (``/go/<key>/``) instead of hard-coding a module URL. The gateway
resolves the key through this map, enforces candidate authentication and then
redirects to the real destination.

Why a gateway instead of plain hrefs
------------------------------------
The Skill Up hub is a single static document whose sections are reached through
the URL *fragment* (``#depth-english``). A fragment never reaches the server, so
``@login_required`` on the hub cannot preserve it: an anonymous click on
``/skill-up/#depth-english`` would come back from the login page on the hub's
home view with the section lost. Sections therefore travel as the ``section``
QUERY parameter, which survives ``?next=`` round-trips intact; the hub template
converts it back into a hash on load.

Every destination below is an EXISTING route. Nothing here creates a page.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from django.urls import reverse


@dataclass(frozen=True)
class Destination:
    """One landing-page navigation target.

    ``url_name``  existing Django URL pattern name — never a hardcoded path.
    ``query``     query parameters appended to it (category / section filters).
    ``protected`` True when the destination requires a logged-in candidate.
                  Mirrors the ``@login_required`` already on the target view;
                  the gateway redirects to login itself so the full target
                  (query parameters included) is preserved in ``?next=``.
    """

    label: str
    url_name: str
    query: dict | None = None
    protected: bool = True

    def path(self) -> str:
        base = reverse(self.url_name)
        if self.query:
            return f"{base}?{urlencode(self.query)}"
        return base


#: key -> Destination. Keys are what the landing page templates reference.
NAV_MAP: dict[str, Destination] = {
    # ── Skill Up menu ────────────────────────────────────────────────────
    # English Learning opens the hub's English & Vocabulary section.
    "english-learning": Destination(
        "English Learning", "skill_up", {"section": "depth-english"}
    ),
    # Grammar is its own module at /subject/ (subject_views.subject_home).
    "grammar": Destination("Grammar", "subject"),
    # "English & Vocabulary" is the `depth-english` article on the hub.
    "vocabulary": Destination(
        "Vocabulary & Idioms", "skill_up", {"section": "depth-english"}
    ),
    # Activities categories come from activities.models.CATEGORY_CHOICES.
    "speaking": Destination(
        "Speaking & Presentation", "activity_list", {"category": "speaking"}
    ),
    "writing": Destination(
        "Writing & Correspondence", "activity_list", {"category": "writing"}
    ),
    "negotiation": Destination(
        "Negotiation & Meetings", "activity_list", {"category": "negotiation"}
    ),
    # Interactive Workshop is the `workshop` Activities category — the same
    # set workshop_dashboard lists. The Roleplay module is one activity inside
    # it, so linking the category (not /roleplay/) opens the whole workshop.
    "workshop": Destination(
        "Interactive Workshop", "activity_list", {"category": "workshop"}
    ),
    # The landing page's "choose a path" cards cover the two remaining
    # Activities categories; they go through the gateway for the same reason.
    "communication": Destination(
        "Professional Communication", "activity_list", {"category": "communication"}
    ),
    "analysis": Destination(
        "Analysis & Reporting", "activity_list", {"category": "analysis"}
    ),
    "aptitude": Destination("Aptitude", "skill_up", {"section": "depth-aptitude"}),
    "tech": Destination("Tech", "skill_up", {"section": "depth-tech"}),
    "certifications": Destination(
        "Certifications", "skill_up", {"section": "section-certifications"}
    ),

    # ── Resources menu ───────────────────────────────────────────────────
    "skill-up-hub": Destination("Skill Up Hub", "skill_up"),
    # "Browse all Skill Up" in the mega-menu footer -> the hub's modules block.
    "browse-all": Destination(
        "Browse all Skill Up", "skill_up", {"section": "section-depth"}
    ),
    "activities": Destination("Activities", "activity_list"),
    # Sitemap is a section of the Skill Up hub, not a separate page — verified
    # against static/001 Career Buddy/index.html (`<section id="section-sitemap">`).
    "sitemap": Destination("Sitemap", "skill_up", {"section": "section-sitemap"}),
    "pro": Destination("CareerBuddy Pro", "pro_page"),

    # ── Other landing-page destinations that need the same login handling ──
    "resume-builder": Destination("Resume Builder", "resume_builder"),
    "job-match": Destination("Find Jobs", "resume_analytics"),
    "dashboard": Destination("Dashboard", "student_dashboard"),
}

#: Section ids the hub is allowed to scroll to. The gateway refuses anything
#: else, so a crafted ``?section=`` can never be reflected into the page.
ALLOWED_SECTIONS = {
    "depth-english",
    "depth-aptitude",
    "depth-tech",
    "depth-nonit",
    "section-depth",
    "section-certifications",
    "section-sitemap",
}


def destination_for(key: str) -> Destination | None:
    return NAV_MAP.get(key)
