"""
Skill Up catalog — the single source of truth for Skill Up structure.

The catalog is DERIVED, never hand-maintained. It is built by parsing the real
Skill Up hub at ``static/001 Career Buddy/index.html``: every ``<article class="sec">``
is a section, every ``<h3>`` inside one is a subsection, and every
``<a class="card" href="#load=...">`` is a lesson.

If a developer adds, renames or removes a lesson in that file, the catalog
reflects it on the next index rebuild — no chatbot rule has to change.

Nothing in this module calls an LLM. Counts, names, hierarchy and routes come
from the filesystem and only from the filesystem.
"""

from __future__ import annotations

import html
import os
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable
from urllib.parse import unquote

from django.conf import settings
from django.core.cache import cache

# ── constants ──────────────────────────────────────────────────────────────

SKILLUP_DIRNAME = "001 Career Buddy"
SKILLUP_INDEX = "index.html"

#: Every Skill Up route Buddy hands to ``performAction()`` is built on this
#: prefix. It must be the Django ``skill_up`` route rather than the raw static
#: file: a static file never passes through the template engine, so navigating
#: there would drop the user onto a Skill Up page with no Buddy on it — the
#: exact problem this integration exists to solve. Resolved lazily because URL
#: configuration is not loaded when this module is first imported.
_HUB_ROUTE_FALLBACK = "/skill-up/"


def hub_route() -> str:
    """Return the site route that serves Skill Up with Buddy attached."""
    try:
        from django.urls import reverse
        return reverse("skill_up")
    except Exception:
        return _HUB_ROUTE_FALLBACK

#: Cache key for the built manifest. Versioned so a code change invalidates it.
CACHE_KEY = "skillup:manifest:v2"
CACHE_TTL = 60 * 60 * 6  # 6 hours; mtime check below makes this a safety net

#: Section hashes that already exist in ACTION_DEFINITIONS. Preserved exactly.
SECTION_HASH_TO_ACTION = {
    "depth-english": "english_vocab",
    "depth-aptitude": "aptitude",
    "depth-tech": "tech",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|template|svg)\b.*?</\1\s*>", re.S | re.I
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

#: Words too generic to identify a lesson. Excluded from alias generation.
GENERIC_ALIASES = {
    "course", "guide", "lesson", "index", "reference", "drill", "notes",
    "study guide", "tutorial", "coach", "series", "basic", "advanced",
    "mastery", "learning", "syllabus", "activity", "test", "practice",
}


def _text(fragment: str) -> str:
    """Strip tags and entities from an HTML fragment, collapsing whitespace."""
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", fragment or ""))).strip()


def normalize_key(value: str) -> str:
    """Aggressive normalisation used for alias and fuzzy matching.

    Lowercases, strips accents and punctuation, collapses whitespace. This is
    what turns 'Gen AI', 'gen-ai' and 'GENAI' into the same lookup key.
    """
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return _WS_RE.sub(" ", value).strip()


def _slug(value: str) -> str:
    return normalize_key(value).replace(" ", "-")[:60] or "item"


# ── data model ─────────────────────────────────────────────────────────────


@dataclass
class Lesson:
    lesson_id: str
    title: str
    description: str
    source_file: str          # relative to the Skill Up root, e.g. "TechCenter/010 genai-course-guide.html"
    route: str                # full navigable route including hash
    hash: str                 # the "#load=..." fragment only
    section_id: str
    section_title: str
    subsection_id: str
    subsection_title: str
    order: int
    aliases: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Subsection:
    subsection_id: str
    title: str
    section_id: str
    section_title: str
    order: int
    lessons: list[Lesson] = field(default_factory=list)

    @property
    def lesson_count(self) -> int:
        return len(self.lessons)


@dataclass
class Section:
    section_id: str           # the DOM hash, e.g. "depth-tech"
    title: str
    action_key: str | None    # existing ACTION_DEFINITIONS key, if any
    route: str
    order: int
    subsections: list[Subsection] = field(default_factory=list)

    @property
    def lessons(self) -> list[Lesson]:
        return [lesson for sub in self.subsections for lesson in sub.lessons]

    @property
    def subsection_count(self) -> int:
        return len(self.subsections)

    @property
    def lesson_count(self) -> int:
        return len(self.lessons)


@dataclass
class Manifest:
    sections: list[Section]
    lessons_by_id: dict[str, Lesson]
    alias_index: dict[str, list[str]]     # normalized alias -> [lesson_id, ...]
    source_index: dict[str, str]          # normalized source_file -> lesson_id
    built_from: str
    fingerprint: str

    # -- counts (deterministic) ---------------------------------------------
    def count_sections(self) -> int:
        return len(self.sections)

    def count_subsections(self, section: Section | None = None) -> int:
        if section is not None:
            return section.subsection_count
        return sum(s.subsection_count for s in self.sections)

    def count_lessons(
        self, section: Section | None = None, subsection: Subsection | None = None
    ) -> int:
        if subsection is not None:
            return subsection.lesson_count
        if section is not None:
            return section.lesson_count
        return len(self.lessons_by_id)


# ── skill up root resolution ───────────────────────────────────────────────


def skillup_root() -> str | None:
    """Absolute path to the Skill Up directory, or None if it is not present.

    Searches every configured static location plus STATIC_ROOT so this works in
    both development and a collectstatic'd deployment.
    """
    candidates: list[str] = []
    for entry in getattr(settings, "STATICFILES_DIRS", []) or []:
        candidates.append(str(entry[1]) if isinstance(entry, (tuple, list)) else str(entry))
    base = getattr(settings, "BASE_DIR", None)
    if base:
        candidates.append(os.path.join(str(base), "static"))
    static_root = getattr(settings, "STATIC_ROOT", None)
    if static_root:
        candidates.append(str(static_root))

    for base_dir in candidates:
        path = os.path.join(base_dir, SKILLUP_DIRNAME)
        if os.path.isfile(os.path.join(path, SKILLUP_INDEX)):
            return os.path.abspath(path)
    return None


def _fingerprint(root: str) -> str:
    """Cheap change-detector: newest mtime + file count across the Skill Up tree.

    Rebuilding the manifest costs a few milliseconds, so a coarse fingerprint is
    enough — we do not need content hashing.
    """
    newest = 0.0
    count = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if not name.lower().endswith((".html", ".htm")):
                continue
            count += 1
            try:
                newest = max(newest, os.path.getmtime(os.path.join(dirpath, name)))
            except OSError:
                continue
    return f"{count}:{newest:.0f}"


# ── parsing ────────────────────────────────────────────────────────────────

_SECTION_RE = re.compile(
    r'<article[^>]*class="[^"]*\bsec\b[^"]*"[^>]*id="(?P<sid>[^"]+)"(?P<body>.*?)</article>',
    re.S | re.I,
)
_H2_RE = re.compile(r"<h2[^>]*>(?P<t>.*?)</h2>", re.S | re.I)
_CARD_RE = re.compile(
    r'<a[^>]*class="[^"]*\bcard\b[^"]*"[^>]*href="#load=(?P<href>[^"]+)"[^>]*>(?P<body>.*?)</a>',
    re.S | re.I,
)
_H3_RE = re.compile(r"<h3[^>]*>(?P<t>.*?)</h3>", re.S | re.I)
_H4_RE = re.compile(r"<h4[^>]*>(?P<t>.*?)</h4>", re.S | re.I)
_P_RE = re.compile(r"<p[^>]*>(?P<t>.*?)</p>", re.S | re.I)
_CHIP_RE = re.compile(r'<span[^>]*class="[^"]*\bchip\b[^"]*"[^>]*>(?P<t>.*?)</span>', re.S | re.I)


def _split_href(raw: str) -> tuple[str, str]:
    """Split a ``#load=<path>&title=<title>`` fragment into (source_file, title)."""
    raw = html.unescape(raw)
    path_part, _, title_part = raw.partition("&title=")
    return unquote(path_part).strip(), unquote(title_part).replace("+", " ").strip()


def _numeric_variants(value: str) -> set[str]:
    """Zero-padding variants of any numbers inside a normalised phrase.

    The hub labels numbered lessons with a padded index ("phonics 01"), but a
    user says "phonics 1". Emit both so either phrasing resolves.
    """
    out: set[str] = set()
    if not value or not re.search(r"\d", value):
        return out
    # unpadded: "phonics 01" -> "phonics 1"
    out.add(re.sub(r"\b0+(\d)", r"\1", value))
    # padded: "phonics 1" -> "phonics 01"
    out.add(re.sub(r"\b(\d)\b", r"0\1", value))
    return {v for v in out if v and v != value}


def _lesson_aliases(title: str, source_file: str, chip: str,
                    nav_title: str = "") -> list[str]:
    """Generate lookup aliases for a lesson from its own metadata only.

    Everything here is derived from the real title, the on-page navigation
    label and the filename — no invented course names. The alias list is what
    makes 'gen ai', 'genai' and 'genai course guide' resolve to the same real
    lesson, and 'cefr a1' / 'phonics 1' reach the numbered lessons whose <h4>
    heading ("Elementary · A1", "Letter sounds") never mentions the series.
    """
    aliases: set[str] = set()

    # The heading, the navigation label ("CEFR A1 · Elementary") and each of
    # that label's dot-separated segments ("cefr a1", "elementary") are all
    # things a user might say. The nav label is often the richest: it carries
    # the series name and level that the card heading drops.
    phrases: list[str] = [title]
    if nav_title:
        phrases.append(nav_title)
        for segment in re.split(r"[·|–—\-:]", nav_title):
            phrases.append(segment)

    for phrase in phrases:
        norm = normalize_key(phrase)
        if not norm:
            continue
        aliases.add(norm)
        aliases.update(_numeric_variants(norm))
        # drop trailing generic nouns so "python learning" also matches "python"
        trimmed = re.sub(
            r"\b(course|guide|tutorial|study guide|notion|reference|mastery|"
            r"learning|principles|series|index|coach|notes)\b",
            " ",
            norm,
        )
        trimmed = _WS_RE.sub(" ", trimmed).strip()
        if trimmed and trimmed != norm:
            aliases.add(trimmed)
        # spaced-out compact forms: "genai" -> "gen ai"
        compact = norm.replace(" ", "")
        if compact:
            aliases.add(compact)
        if trimmed:
            aliases.add(trimmed.replace(" ", ""))

    stem = os.path.splitext(os.path.basename(source_file))[0]
    stem_norm = normalize_key(re.sub(r"^\d+\s*", "", stem))
    if stem_norm:
        aliases.add(stem_norm)
        aliases.add(stem_norm.replace(" ", ""))
        aliases.update(_numeric_variants(stem_norm))

    chip_norm = normalize_key(chip)
    if chip_norm and 2 <= len(chip_norm) <= 12 and chip_norm not in GENERIC_ALIASES:
        aliases.add(chip_norm)

    # A generic word must never become an alias on its own, or "xyz course"
    # would resolve to whichever lesson happens to carry a "Course" chip.
    return sorted(a for a in aliases if len(a) >= 2 and a not in GENERIC_ALIASES)


def build_manifest(root: str) -> Manifest:
    """Parse the Skill Up hub into a Manifest. Pure function of the filesystem."""
    index_path = os.path.join(root, SKILLUP_INDEX)
    with open(index_path, encoding="utf-8", errors="replace") as handle:
        markup = handle.read()

    # The sitemap block repeats the same links in a different layout. Parsing
    # only <article class="sec"> blocks keeps each lesson counted exactly once.
    sections: list[Section] = []
    lessons_by_id: dict[str, Lesson] = {}
    alias_index: dict[str, list[str]] = {}
    source_index: dict[str, str] = {}

    for s_order, s_match in enumerate(_SECTION_RE.finditer(markup)):
        section_id = s_match.group("sid")
        body = s_match.group("body")
        h2 = _H2_RE.search(body)
        section_title = _text(h2.group("t")) if h2 else section_id
        action_key = SECTION_HASH_TO_ACTION.get(section_id)

        section = Section(
            section_id=section_id,
            title=section_title,
            action_key=action_key,
            route=f"{hub_route()}#{section_id}",
            order=s_order,
        )

        # Walk the section body in document order, tracking the current <h3>.
        markers: list[tuple[int, str, Any]] = []
        for m in _H3_RE.finditer(body):
            markers.append((m.start(), "h3", m))
        for m in _CARD_RE.finditer(body):
            markers.append((m.start(), "card", m))
        markers.sort(key=lambda item: item[0])

        current: Subsection | None = None
        sub_order = 0
        for _pos, kind, m in markers:
            if kind == "h3":
                title = _text(m.group("t"))
                current = Subsection(
                    subsection_id=f"{section_id}--{_slug(title)}",
                    title=title,
                    section_id=section_id,
                    section_title=section_title,
                    order=sub_order,
                )
                sub_order += 1
                section.subsections.append(current)
                continue

            if current is None:
                # A card before any <h3>: park it in an implicit subsection so
                # nothing is silently dropped from the counts.
                current = Subsection(
                    subsection_id=f"{section_id}--general",
                    title=section_title,
                    section_id=section_id,
                    section_title=section_title,
                    order=sub_order,
                )
                sub_order += 1
                section.subsections.append(current)

            source_file, href_title = _split_href(m.group("href"))
            card_body = m.group("body")
            h4 = _H4_RE.search(card_body)
            para = _P_RE.search(card_body)
            chip = _CHIP_RE.search(card_body)
            title = _text(h4.group("t")) if h4 else (href_title or source_file)
            description = _text(para.group("t")) if para else ""
            chip_text = _text(chip.group("t")) if chip else ""

            lesson_id = f"{section_id}--{_slug(title)}"
            suffix = 2
            while lesson_id in lessons_by_id:
                lesson_id = f"{section_id}--{_slug(title)}-{suffix}"
                suffix += 1

            hash_fragment = f"#load={m.group('href')}"
            lesson = Lesson(
                lesson_id=lesson_id,
                title=title or href_title,
                description=description,
                source_file=source_file,
                route=f"{hub_route()}{hash_fragment}",
                hash=hash_fragment,
                section_id=section_id,
                section_title=section_title,
                subsection_id=current.subsection_id,
                subsection_title=current.title,
                order=len(current.lessons),
                aliases=_lesson_aliases(title or href_title, source_file, chip_text,
                                        nav_title=href_title),
                keywords=sorted(set(normalize_key(description).split()) - {""}),
            )
            current.lessons.append(lesson)
            lessons_by_id[lesson_id] = lesson
            source_index[normalize_key(source_file)] = lesson_id
            for alias in lesson.aliases:
                alias_index.setdefault(alias, []).append(lesson_id)

        sections.append(section)

    return Manifest(
        sections=sections,
        lessons_by_id=lessons_by_id,
        alias_index=alias_index,
        source_index=source_index,
        built_from=index_path,
        fingerprint=_fingerprint(root),
    )


# ── cached accessor ────────────────────────────────────────────────────────

_MEMO: dict[str, Any] = {"manifest": None, "fingerprint": None}


def get_manifest(force: bool = False) -> Manifest | None:
    """Return the cached Manifest, rebuilding it only when Skill Up changed.

    Two layers: a process-local memo (so a single request never re-parses) and
    the Django cache (so workers share the work). Both are keyed on a
    filesystem fingerprint, which is what gives automatic re-indexing.
    """
    root = skillup_root()
    if root is None:
        return None

    fingerprint = _fingerprint(root)

    if not force:
        memo = _MEMO.get("manifest")
        if memo is not None and _MEMO.get("fingerprint") == fingerprint:
            return memo
        cached = cache.get(CACHE_KEY)
        if cached is not None and getattr(cached, "fingerprint", None) == fingerprint:
            _MEMO["manifest"] = cached
            _MEMO["fingerprint"] = fingerprint
            return cached

    manifest = build_manifest(root)
    _MEMO["manifest"] = manifest
    _MEMO["fingerprint"] = manifest.fingerprint
    try:
        cache.set(CACHE_KEY, manifest, CACHE_TTL)
    except Exception:
        # A cache backend that cannot pickle the manifest must not break chat.
        pass
    return manifest


def invalidate() -> None:
    _MEMO["manifest"] = None
    _MEMO["fingerprint"] = None
    try:
        cache.delete(CACHE_KEY)
    except Exception:
        pass
