"""
SkillUpKnowledgeService — the only component allowed to answer Skill Up facts.

Grounding levels (see the implementation spec):

    LEVEL 1  structure   counts, names, hierarchy      -> catalog, deterministic
    LEVEL 2  metadata    which section/subsection/route -> catalog, deterministic
    LEVEL 3  content     what a page actually teaches   -> real HTML, retrieved

The LLM is never consulted for level 1 or 2, and for level 3 it only ever sees
text this module extracted from a file the catalog vouches for.
"""

from __future__ import annotations

import html
import os
import re
from functools import lru_cache
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import unquote

from django.core.cache import cache

from .skillup_catalog import (
    SKILLUP_DIRNAME,
    Lesson,
    Manifest,
    Place,
    Section,
    Subsection,
    get_manifest,
    normalize_key,
    skillup_root,
    _SCRIPT_STYLE_RE,
    _COMMENT_RE,
    _TAG_RE,
    _WS_RE,
)

def _text_of(fragment: str) -> str:
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", fragment or ""))).strip()


# ── query normalisation helpers ────────────────────────────────────────────

#: Abbreviations users actually type. Every value expands to wording that
#: appears in the real catalog — this map never introduces a new entity.
ABBREVIATIONS = {
    "db": "database",
    "dbs": "database",
    "vectordb": "vector database",
    "genai": "gen ai generative ai",
    "gen ai": "genai generative ai",
    "generative ai": "genai",
    "ux": "user experience design",
    "ui": "user interface design",
    "ui ux": "ui ux design",
    "quant": "quantitative aptitude",
    "quants": "quantitative aptitude",
    "logic": "logical reasoning",
    "oop": "oop mastery object oriented",
    "dsa": "dsa data structures algorithms",
    "nlp": "nltk nlp",
    "ml": "machine learning",
    "prompting": "prompt engineering",
    "prompt": "prompt engineering",
    "crew ai": "crewai",
    "crewai": "crew ai",
    "devops": "devops infrastructure",
    "english": "english vocabulary cefr",
    "maths": "quantitative aptitude",
    "math": "quantitative aptitude",
}

_STOPWORDS = {
    "the", "a", "an", "of", "for", "to", "in", "on", "me", "my", "i", "is",
    "are", "what", "which", "show", "open", "go", "take", "find", "want",
    "learn", "about", "please", "can", "you", "there", "here", "this", "it",
    "and", "or", "how", "many", "much", "does", "do", "page", "lesson",
    "course", "section", "skill", "up", "skillup", "module",
}


def _expand(query: str) -> str:
    norm = normalize_key(query)
    if not norm:
        return ""
    parts = [norm]
    for abbr, expansion in ABBREVIATIONS.items():
        if re.search(rf"\b{re.escape(abbr)}\b", norm):
            parts.append(expansion)
            # Substitute in place as well, so "vector db" also produces the
            # contiguous phrase "vector database" and not just loose tokens.
            parts.append(re.sub(rf"\b{re.escape(abbr)}\b", expansion, norm))
    # also try the de-spaced form so "gen ai" reaches "genai"
    parts.append(norm.replace(" ", ""))
    return " ".join(parts)


def _stem(token: str) -> str:
    """Very small stemmer: plural -> singular.

    Without this, "databases" and "database" are different tokens and the
    lexical gate rejects a lesson that is plainly about databases.
    """
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("es") and not token.endswith("ses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


@lru_cache(maxsize=16384)
def _tokens(value: str) -> frozenset[str]:
    raw = {t for t in normalize_key(value).split() if t and t not in _STOPWORDS}
    return frozenset(raw | {_stem(t) for t in raw})


# ── match result ───────────────────────────────────────────────────────────


@dataclass
class Match:
    kind: str                 # "lesson" | "subsection" | "section"
    obj: Any
    score: float
    title: str
    route: str


@dataclass
class SkillUpContext:
    """What the user is currently looking at inside Skill Up."""
    in_skillup: bool = False
    section: Section | None = None
    subsection: Subsection | None = None
    lesson: Lesson | None = None

    def describe(self) -> str:
        if not self.in_skillup:
            return ""
        bits = ["Module: Skill Up"]
        if self.section:
            bits.append(f"Section: {self.section.title}")
        if self.subsection:
            bits.append(f"Subsection: {self.subsection.title}")
        if self.lesson:
            bits.append(f"Lesson: {self.lesson.title}")
            bits.append(f"Source file: {self.lesson.source_file}")
        return " | ".join(bits)


class SkillUpKnowledgeService:
    """Facade over the catalog. Construct per request; the manifest is cached."""

    # ── lifecycle ──────────────────────────────────────────────────────────

    def __init__(self, manifest: Manifest | None = None):
        self.manifest = manifest if manifest is not None else get_manifest()

    @property
    def available(self) -> bool:
        return self.manifest is not None and bool(self.manifest.sections)

    # ── LEVEL 1: structure ─────────────────────────────────────────────────

    def get_sections(self) -> list[Section]:
        return list(self.manifest.sections) if self.available else []

    def get_section(self, name: str) -> Section | None:
        if not self.available:
            return None
        norm = normalize_key(name)
        compact = norm.replace(" ", "")
        for section in self.manifest.sections:
            title = normalize_key(section.title)
            if norm in (title, section.section_id) or compact == title.replace(" ", ""):
                return section
        # Token-aware partial match. Plain string similarity is not enough:
        # "tech" vs "tech center" scores only 0.53, so a threshold high enough
        # to avoid false matches would reject the obvious one.
        qtokens = _tokens(name)
        best, best_score = None, 0.0
        for section in self.manifest.sections:
            title_norm = normalize_key(section.title)
            score = self._similarity(norm, title_norm)
            ttokens = _tokens(section.title)
            if qtokens and ttokens and qtokens <= ttokens:
                score = max(score, 0.95)          # "tech" ⊂ {"tech","center"}
            elif title_norm.startswith(norm) and len(norm) >= 3:
                score = max(score, 0.9)
            if score > best_score:
                best, best_score = section, score
        return best if best_score >= 0.6 else None

    def get_subsections(self, section: Section | str | None = None) -> list[Subsection]:
        if not self.available:
            return []
        if section is None:
            return [sub for s in self.manifest.sections for sub in s.subsections]
        if isinstance(section, str):
            section = self.get_section(section)
        return list(section.subsections) if section else []

    def get_subsection(self, name: str, section: Section | None = None) -> Subsection | None:
        pool = self.get_subsections(section)
        norm = normalize_key(name)
        for sub in pool:
            if normalize_key(sub.title) == norm:
                return sub
        qtokens = _tokens(name)
        best, best_score = None, 0.0
        for sub in pool:
            score = self._similarity(norm, normalize_key(sub.title))
            stokens = _tokens(sub.title)
            if qtokens and stokens and qtokens <= stokens:
                score = max(score, 0.95)
            if score > best_score:
                best, best_score = sub, score
        return best if best_score >= 0.62 else None

    def get_lessons(self, section: Any = None, subsection: Any = None) -> list[Lesson]:
        if not self.available:
            return []
        if subsection is not None:
            if isinstance(subsection, str):
                subsection = self.get_subsection(subsection)
            return list(subsection.lessons) if subsection else []
        if section is not None:
            if isinstance(section, str):
                section = self.get_section(section)
            return list(section.lessons) if section else []
        return list(self.manifest.lessons_by_id.values())

    def count_sections(self) -> int:
        return self.manifest.count_sections() if self.available else 0

    def count_subsections(self, section: Any = None) -> int:
        if not self.available:
            return 0
        if isinstance(section, str):
            section = self.get_section(section)
        return self.manifest.count_subsections(section)

    def count_lessons(self, section: Any = None, subsection: Any = None) -> int:
        if not self.available:
            return 0
        if isinstance(section, str):
            section = self.get_section(section)
        if isinstance(subsection, str):
            subsection = self.get_subsection(subsection, section)
        return self.manifest.count_lessons(section, subsection)

    # ── LEVEL 2: resolution and search ─────────────────────────────────────

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def _lexically_related(qtokens: set[str], query: str, title: str,
                           extra: set[str] | None = None) -> bool:
        """Gate before any fuzzy score is trusted.

        Character similarity alone is noise across unrelated words —
        "blockchain" scores ~0.35 against "logical reasoning", which is enough
        to clear a loose search threshold and invent a match. Require a real
        lexical link: a shared token, or a substring hit, or near-identity.
        """
        ttokens = _tokens(title) | (extra or set())
        if qtokens & ttokens:
            return True
        tnorm = normalize_key(title)
        if query and (query in tnorm or tnorm in query):
            return True
        # allow prefix/typo relationships on a single token ("crewai"/"crew ai")
        qflat, tflat = query.replace(" ", ""), tnorm.replace(" ", "")
        if qflat and tflat and (qflat in tflat or tflat in qflat):
            return True
        sm = SequenceMatcher(None, qflat, tflat)
        return sm.real_quick_ratio() >= 0.8 and sm.quick_ratio() >= 0.8 and sm.ratio() >= 0.8

    def _score_lesson(self, query: str, expanded: str, qtokens: set[str], lesson: Lesson) -> float:
        title_norm = normalize_key(lesson.title)
        best = 0.0

        # exact alias hit is decisive
        for alias in lesson.aliases:
            if alias == query or alias == query.replace(" ", ""):
                best = 1.0
                break
            if alias and (alias in expanded or alias.replace(" ", "") in expanded.replace(" ", "")):
                best = max(best, 0.9)

        if query and query in title_norm:
            best = max(best, 0.85)
        if query and query.replace(" ", "") and query.replace(" ", "") in title_norm.replace(" ", ""):
            best = max(best, 0.82)

        # token overlap against title
        ttokens = _tokens(lesson.title)
        if qtokens and ttokens:
            overlap = len(qtokens & ttokens) / len(qtokens)
            best = max(best, overlap * 0.8)

        # fuzzy title similarity, and against the expanded query
        best = max(best, self._similarity(query, title_norm) * 0.7)
        best = max(best, self._similarity(expanded, title_norm) * 0.6)

        # description / subsection only ever act as weak tie-breakers so a
        # keyword in prose can never outrank a real title match
        dtokens = set(lesson.keywords)
        if qtokens and dtokens:
            best = max(best, (len(qtokens & dtokens) / len(qtokens)) * 0.45)
        stokens = _tokens(lesson.subsection_title)
        if qtokens and stokens:
            best = max(best, (len(qtokens & stokens) / len(qtokens)) * 0.5)

        # Container tie-breaker — applied ONLY to an exact-alias match, so it
        # can only reorder lessons that are already equally, exactly named; it
        # can never let a fuzzy match leapfrog an exact one. When a query token
        # names the lesson's GROUP (its subsection or section) but is absent
        # from the lesson's own title, that token is locating the lesson, so
        # reward it. This is what makes "cefr b1" open the CEFR-levels lesson
        # ("Intermediate · B1", whose subsection is "CEFR levels") outright
        # rather than tie with the equally-named "Vocabulary · CEFR B1", which
        # already carries "cefr" in its own title and so gains nothing here.
        if best >= 1.0:
            title_tokens = _tokens(lesson.title)
            container_tokens = stokens | _tokens(lesson.section_title)
            if (qtokens & container_tokens) - title_tokens:
                # A flat, decisive step so it clears the ambiguity band (0.12).
                best += 0.15
        return best

    def resolve(self, query: str, limit: int = 6, threshold: float = 0.5) -> list[Match]:
        memo = self.manifest.__dict__.setdefault("_resolve_memo", {}) if self.available else None
        key = (query, limit, threshold)
        if memo is not None and key in memo:
            return list(memo[key])
        found = self._resolve(query, limit, threshold)
        if memo is not None:
            if len(memo) > 2000:
                memo.clear()
            memo[key] = found
        return list(found)

    def _resolve(self, query: str, limit: int = 6, threshold: float = 0.5) -> list[Match]:
        """Rank real Skill Up entities against a free-text query.

        Returns only entities that exist. An empty list means 'not found' — it
        is never padded with a best guess.
        """
        if not self.available or not query:
            return []
        norm = normalize_key(query)
        expanded = _expand(query)
        qtokens = _tokens(query) or _tokens(expanded)

        matches: list[Match] = []

        for section in self.manifest.sections:
            if self._lexically_related(qtokens, norm, section.title):
                score = max(
                    self._similarity(norm, normalize_key(section.title)),
                    1.0 if normalize_key(section.title) == norm else 0.0,
                    # same words ("english and vocabulary" = "English & Vocabulary",
                    # "non it center" = "Non-IT Center"): the section, above any lesson
                    1.6 if qtokens and _tokens(section.title) == qtokens else 0.0,
                )
                stoks = _tokens(section.title)
                if qtokens and stoks:
                    score = max(score, len(qtokens & stoks) / len(qtokens) * 0.9)
                if score >= threshold:
                    matches.append(
                        Match("section", section, score, section.title, section.route)
                    )

            for sub in section.subsections:
                if not self._lexically_related(qtokens, norm, sub.title):
                    continue
                sscore = self._similarity(norm, normalize_key(sub.title))
                subtoks = _tokens(sub.title)
                if qtokens and subtoks:
                    sscore = max(sscore, len(qtokens & subtoks) / len(qtokens) * 0.88)
                if sscore >= threshold:
                    matches.append(
                        Match("subsection", sub, sscore, sub.title, section.route)
                    )

        for lesson in self.manifest.lessons_by_id.values():
            # Aliases and description keywords count as lexical evidence for a
            # lesson, so "rag" can still reach a lesson that lists it.
            extra = set(lesson.keywords) | {t for a in lesson.aliases for t in a.split()}
            if not self._lexically_related(qtokens, norm, lesson.title, extra):
                continue
            score = self._score_lesson(norm, expanded, qtokens, lesson)
            if score >= threshold:
                matches.append(Match("lesson", lesson, score, lesson.title, lesson.route))

        # Departments and roles (Tech and Non-IT). Their exact name outranks every
        # course, so "open frontend developer" opens the role, not one of its courses.
        compact = norm.replace(" ", "")
        # "open the development department" / "frontend developer role"
        ptarget = (qtokens - _tokens("department departments dept role roles")) or qtokens
        for place in self.manifest.places:
            ptitle = normalize_key(place.title)
            # Same words count as the exact name: the message arrives with filler
            # such as "of" stripped ("head of pmc ..." -> "head pmc ...").
            ptoks = _tokens(place.title)
            base = _tokens(re.sub(r"\(.*?\)", " ", place.title))   # "(PMM)" is optional
            abbrevs = [_tokens(x) for x in re.findall(r"\(([^)]*)\)", place.title)]   # "(SDE)"
            is_dept = place.place_id.startswith("grp-")
            if ptitle == norm or ptitle.replace(" ", "") == compact or (ptarget and ptoks == ptarget):
                # typed as written: clearly above everything else ("Product Owner"
                # over "Product Owner (PO)", "Fire Safety" over the HSE department)
                score = 1.6
            elif ptarget and (base == ptarget or ptarget in abbrevs):
                score = 1.45
            elif place.department and base and base < ptarget and ptarget - base <= _tokens(place.department):
                # "devops engineer in devops infrastructure": role name + its department.
                # Below an exact name, so the department "Quality & Inspection Skills"
                # still wins over its role "Quality Inspection".
                score = 1.3
            elif len(ptarget) >= 2 and ptarget <= ptoks:
                # Every word given is in this name: "agile and delivery" ->
                # "Project Management / Agile & Delivery". Tighter names rank higher,
                # and a department ranks above a role that shares the words
                # ("customer success" -> the department, not Customer Success Manager).
                score = 1.2 - 0.02 * len(ptoks - ptarget) + (0.2 if is_dept else 0.0)
            elif is_dept and len(ptarget) == 1 and ptarget <= ptoks:
                # One word of a department name ("payroll", "design"). Kept just
                # below an exact lesson name, so "writing" still opens the lesson.
                score = 0.95
            elif not self._lexically_related(qtokens, norm, place.title):
                continue
            else:
                score = max(self._similarity(norm, ptitle) * 0.85,
                            (len(qtokens & ptoks) / len(qtokens)) * 0.8 if qtokens and ptoks else 0.0)
            if score >= threshold:
                matches.append(Match("place", place, score, place.title, place.route))

        matches.sort(key=lambda m: (-m.score, m.kind != "lesson", m.title))
        return matches[:limit]

    def search(self, query: str, limit: int = 6) -> list[Match]:
        """Looser than resolve() — used for 'find me something about X'."""
        return self.resolve(query, limit=limit, threshold=0.34)

    def is_ambiguous(self, matches: list[Match]) -> bool:
        """True when the top two candidates are too close to pick between."""
        if len(matches) < 2:
            return False
        top, second = matches[0], matches[1]
        if top.score >= 0.99 and second.score < 0.99:
            return False
        return (top.score - second.score) < 0.12

    def get_lesson(self, name_or_alias: str) -> Lesson | None:
        matches = [m for m in self.resolve(name_or_alias) if m.kind == "lesson"]
        if not matches:
            return None
        if self.is_ambiguous(matches):
            return None
        return matches[0].obj

    # ── current page awareness ─────────────────────────────────────────────

    def get_current_context(self, path: str = "", page: str = "", hash_value: str = "") -> SkillUpContext:
        """Work out where inside Skill Up the user is, from path + hash.

        Handles all three route shapes the hub actually uses:
        ``#depth-<section>``, ``#section-<block>`` and
        ``#load=<file>&title=<title>``.
        """
        ctx = SkillUpContext()
        if not self.available:
            return ctx

        blob = f"{path or ''} {page or ''} {hash_value or ''}"
        if SKILLUP_DIRNAME.lower() not in blob.lower() and "skill" not in normalize_key(blob):
            return ctx
        ctx.in_skillup = True

        fragment = hash_value or ""
        if "#" in blob and not fragment:
            fragment = blob[blob.index("#"):]
        # Match against the still-encoded fragment: Skill Up filenames contain
        # spaces ("010 genai-course-guide.html"), so unquoting first would let
        # the path terminate at the first %20.
        load_match = re.search(r"#?load=([^&\s]+)", fragment)
        if load_match:
            source = unquote(load_match.group(1)).strip()
            lesson_id = self.manifest.source_index.get(normalize_key(source))
            if lesson_id:
                lesson = self.manifest.lessons_by_id[lesson_id]
                ctx.lesson = lesson
                ctx.section = self.get_section(lesson.section_title)
                ctx.subsection = next(
                    (s for s in self.get_subsections(ctx.section)
                     if s.subsection_id == lesson.subsection_id),
                    None,
                )
                return ctx

        depth_match = re.search(r"#?(depth-[a-z]+)", unquote(fragment))
        if depth_match:
            section_id = depth_match.group(1)
            ctx.section = next(
                (s for s in self.manifest.sections if s.section_id == section_id), None
            )
        return ctx

    # ── LEVEL 3: page content ──────────────────────────────────────────────

    def _safe_path(self, source_file: str) -> str | None:
        """Resolve a catalog-supplied relative path to an absolute file.

        Two independent guards: the path must already be present in the catalog
        (so it came from the trusted index, not from the model or the browser),
        and the resolved absolute path must still sit inside the Skill Up root
        after normalisation. Traversal attempts fail both.
        """
        if normalize_key(source_file) not in self.manifest.source_index:
            return None
        root = skillup_root()
        if not root:
            return None
        candidate = os.path.abspath(os.path.join(root, source_file))
        if os.path.commonpath([candidate, os.path.abspath(root)]) != os.path.abspath(root):
            return None
        if not os.path.isfile(candidate):
            return None
        return candidate

    #: Phrases that, inside retrieved page text, would be an attempt to steer
    #: the model. They are neutralised rather than removed so a page that
    #: legitimately discusses prompt injection still reads sensibly.
    _INJECTION_RE = re.compile(
        r"(ignore\s+(all\s+)?(previous|prior|above)\s+instructions?"
        r"|disregard\s+(the\s+)?(previous|prior|above|system)"
        r"|you\s+are\s+now\s+"
        r"|system\s*prompt\s*:"
        r"|<\s*NAV\s*:[^>]*>"
        r"|new\s+instructions?\s*:)",
        re.I,
    )

    def get_page_content(self, lesson: Lesson, max_chars: int = 6000) -> str:
        """Extract readable text from a real Skill Up page.

        Scripts, styles, comments and SVG are dropped before any text is taken,
        so tracking code and markup never reach the model. The result is
        cached per lesson.
        """
        cache_key = f"skillup:content:{lesson.lesson_id}:{max_chars}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        path = self._safe_path(lesson.source_file)
        if not path:
            return ""
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                markup = handle.read()
        except OSError:
            return ""

        markup = _SCRIPT_STYLE_RE.sub(" ", markup)
        markup = _COMMENT_RE.sub(" ", markup)

        chunks: list[str] = []
        for match in re.finditer(
            r"<(h1|h2|h3|h4|h5|li|p|td|th|figcaption|blockquote)\b[^>]*>(.*?)</\1\s*>",
            markup,
            re.S | re.I,
        ):
            tag = match.group(1).lower()
            text = _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", match.group(2)))).strip()
            if not text or len(text) < 2:
                continue
            if tag.startswith("h"):
                chunks.append(f"\n## {text}")
            elif tag == "li":
                chunks.append(f"- {text}")
            else:
                chunks.append(text)

        if len("".join(chunks).strip()) < 120:
            # Several Skill Up pages (the phonics and vocabulary activities)
            # are built entirely from <div>/<span> with no <p> or heading tags.
            # Fall back to leaf-node text so those pages are still grounded
            # rather than silently returning nothing.
            chunks = []
            title_match = re.search(r"<title[^>]*>(.*?)</title>", markup, re.S | re.I)
            if title_match:
                chunks.append(f"## {_text_of(title_match.group(1))}")
            for match in re.finditer(
                r"<(div|span|section|article)\b[^>]*>(?P<inner>[^<]{3,400})</\1\s*>",
                markup, re.S | re.I,
            ):
                text = _text_of(match.group("inner"))
                if text and len(text) >= 3:
                    chunks.append(text)
            seen: set[str] = set()
            deduped = []
            for chunk in chunks:
                if chunk not in seen:
                    seen.add(chunk)
                    deduped.append(chunk)
            chunks = deduped

        body = "\n".join(chunks)
        body = self._INJECTION_RE.sub("[instruction-like text removed]", body)
        body = _WS_RE.sub(" ", body.replace("\n", "\n")).strip()
        # re-introduce the structural newlines the collapse above flattened
        body = re.sub(r" (## )", r"\n\1", body)
        body = re.sub(r" (- )", r"\n\1", body)

        if len(body) > max_chars:
            body = body[:max_chars].rsplit(" ", 1)[0] + " …"

        cache.set(cache_key, body, 60 * 60)
        return body

    def get_page_summary_context(self, lesson: Lesson) -> dict[str, Any]:
        """The grounded bundle handed to the AI layer for a page question."""
        return {
            "title": lesson.title,
            "section": lesson.section_title,
            "subsection": lesson.subsection_title,
            "catalog_description": lesson.description,
            "source_file": lesson.source_file,
            "page_content": self.get_page_content(lesson),
        }

    def get_page_headings(self, lesson: Lesson) -> list[str]:
        """Real headings on the page — used for 'what topics are covered?'."""
        content = self.get_page_content(lesson, max_chars=20000)
        return [line[3:].strip() for line in content.split("\n") if line.startswith("## ")]

    # ── navigation ─────────────────────────────────────────────────────────

    def get_navigation_route(self, entity: Any) -> str | None:
        """Trusted route for a catalog entity. Never accepts a raw string URL."""
        if isinstance(entity, Lesson):
            return entity.route
        if isinstance(entity, (Section, Place)):
            return entity.route
        if isinstance(entity, Subsection):
            section = next(
                (s for s in self.manifest.sections if s.section_id == entity.section_id), None
            )
            return section.route if section else None
        return None

    def route_is_trusted(self, route: str) -> bool:
        """Server-side validation: a route must belong to a catalog entity."""
        if not self.available or not route:
            return False
        known = {s.route for s in self.manifest.sections}
        known |= {l.route for l in self.manifest.lessons_by_id.values()}
        known |= {p.route for p in self.manifest.places}
        return route in known
