"""Does an uploaded resume fit the role picked on the career-path page?

The role's required skills come from the same data the career-path pages and
Skill Up use (static/data/it_departments.json and nonit_departments.json).
A resume fits when it shows MIN_COVERAGE of the role's skill words and, for
a recruiting/staffing role, shows recruiting work too (FUNCTION_TERMS): an IT
staffing recruiter's skill list is tech words, which a developer's resume
also has. The question bank's taxonomy (role_bank_topics) then decides which
domain questions the interview draws from.
"""
import json
import os
import re
from functools import lru_cache

from django.conf import settings

from .resume_utils import _matching_bank_topics, BANK_TOPICS

ROLE_DATA_FILES = {'tech': 'it_departments.json', 'nonit': 'nonit_departments.json'}

# Share of the role's skill words the resume must contain. (A bank-industry
# overlap test was tried and dropped: its guess disagreed even for resumes
# copied from the role's own skill list.)
MIN_COVERAGE = 0.25

# Roles whose title names one of these kinds of work need a resume that shows it.
FUNCTION_TERMS = [
    (r'recruit|talent acquisition|sourcing|staffing|headhunt|executive search',
     r'recruit|talent acquisition|sourc(e|ed|ing)|staffing|headhunt|hiring|executive search'),
]

# Filler that appears in role skill lines without saying anything about the role.
_FILLER = set(
    'with from that this your their into using such basic core modern advanced management skills '
    'knowledge understanding tools tooling practices fundamentals experience across within including '
    'based level awareness and the for of in on to or a an'.split()
)


# Too common across fields to show on their own that a skill is present.
_GENERIC = set('data system systems process processes design development operations operation '
               'control quality planning service services support team work'.split())


def _key(text):
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')


@lru_cache(maxsize=1)
def _roles():
    """{(track, dept_key, role_key): (dept, role, [skill lines])} from the static data."""
    base = os.path.join(settings.BASE_DIR, 'static', 'data')
    out = {}
    for track, name in ROLE_DATA_FILES.items():
        with open(os.path.join(base, name), encoding='utf-8') as fh:
            for _group, depts in json.load(fh):
                for dept in depts:
                    for role in dept[2]:
                        out[(track, _key(dept[0]), _key(role[0]))] = (dept[0], role[0], list(role[1]))
    return out


@lru_cache(maxsize=1)
def _template_roles():
    """Predefined resume templates (resume_roles.py). Their role cards send the
    template's subtitle as the department, e.g. ('Frontend, backend, full-stack', 'Software Developer')."""
    from .resume_roles import client_payload
    return {('tech' if r['category'] == 'it' else 'nonit', _key(r['subtitle']), _key(r['title'])):
            (r['subtitle'], r['title'], list(r.get('required_skills') or []))
            for r in client_payload()['roles']}


def find_role(track, dept, role):
    """(dept, role, skills) for a role picked on the career-path page, or None."""
    key = (track, _key(dept), _key(role))
    return _roles().get(key) or _template_roles().get(key)


def role_text(dept, role, skills):
    return f"{role} ({dept}). Required skills: " + '; '.join(skills)


def _words(text):
    return {w for w in re.findall(r'[a-z][a-z+#]{2,}', (text or '').lower()) if w not in _FILLER}


def role_skill_groups(skills):
    """Role skill lines -> [(items, any_of)].

    'Databases: Relational databases (PostgreSQL, MySQL), basic SQL querying'
    -> (['Relational databases (PostgreSQL, MySQL)', 'basic SQL querying'], False)
    'Core Languages: Python, Java, C++, or C#'  (", or" = pick one)
    -> (['Python', 'Java', 'C++', 'C#'], True)
    """
    groups, seen = [], set()
    for line in skills:
        body = line.split(':', 1)[1] if ':' in line else line
        any_of = bool(re.search(r',\s*or\s', body))
        items = []
        for part in re.split(r',(?![^()]*\))', body):   # commas outside brackets
            part = re.sub(r'^\s*(?:or|and)\s+', '', part).strip(' .;')
            if part and part.lower() not in seen:
                seen.add(part.lower())
                items.append(part)
        if items:
            groups.append((items, any_of))
    return groups


def _phrase_in(phrase, resume_low):
    phrase = phrase.strip().lower()
    return bool(phrase) and re.search(
        r'(?<![a-z0-9])' + re.escape(phrase) + r'(?![a-z0-9])', resume_low) is not None


def _has_skill(item, resume_words, resume_low):
    core = re.sub(r'\([^)]*\)', ' ', item)
    # Filler-free phrase ("basic CI/CD awareness" -> "ci/cd"), the phrase as
    # written, and any alternative it names: "GitHub/GitLab", "(PostgreSQL, MySQL)".
    trimmed = ' '.join(w for w in re.findall(r'\S+', core.lower()) if w not in _FILLER)
    candidates = [item, core, trimmed]
    candidates += [a for chunk in re.findall(r'\(([^)]*)\)', item) for a in re.split(r'[,/]', chunk)]
    if '/' in trimmed and ' ' not in trimmed:
        candidates += trimmed.split('/')
    if any(_phrase_in(c, resume_low) for c in candidates):
        return True
    # Word overlap as the last resort; generic words alone ("data" from
    # "sales data") must not stand in for "Data Structures".
    words = _words(core)
    specific = words - _GENERIC or words
    return bool(words) and bool(specific & resume_words) and len(words & resume_words) / len(words) >= 0.5


def split_role_skills(resume_text, skills):
    """(matching, missing) role skills for this resume. In a pick-one line
    ("Python, Java, C++, or C#") having any of them covers the line."""
    resume_low = (resume_text or '').lower()
    resume_words = _words(resume_text)
    matching, missing = [], []
    for items, any_of in role_skill_groups(skills):
        have = [i for i in items if _has_skill(i, resume_words, resume_low)]
        matching += have
        if not (any_of and have):
            missing += [i for i in items if i not in have]
    return matching, missing


def role_bank_topics(dept, role, skills):
    """(question-bank topics for this role, how they were found).

    The department/role NAME naming a bank topic is the reliable signal
    ("HSE, Fire & Industrial Safety Workforce", "Python Developer"). Failing
    that, the skills must name at least two topics: a single stray hit is
    noise ("A/B testing" -> "testing" for a Product Manager). Roles the bank
    does not cover get ([], 'none').
    """
    named = _matching_bank_topics(f'{role} {dept}', [])
    if named:
        return named, 'name'
    by_skill = _matching_bank_topics(' '.join(skills), [])
    return (by_skill, 'skills') if len(by_skill) >= 2 else ([], 'none')


def topic_industries(topics, limit=5):
    """Bank industries holding these topics, most questions first."""
    from django.db.models import Count
    from .models import FAQQuestion
    if not topics:
        return []
    rows = (FAQQuestion.objects.filter(topic__in=topics).exclude(topic__in=BANK_TOPICS).exclude(industry='')
            .values('industry').annotate(n=Count('id')).order_by('-n')[:limit])
    return [r['industry'] for r in rows]


def assess_role_fit(resume_text, track, dept, role):
    """{'known', 'ok', 'coverage', 'industries', 'text', 'matching_skills', 'missing_skills'}.

    known=False (role not in the data) means "cannot judge" and is never a
    block: the interview then falls back to the resume's own domain.
    """
    found = find_role(track, dept, role)
    if not found:
        return {'known': False, 'ok': True, 'coverage': None, 'topics': [], 'industries': [], 'text': '',
                'matching_skills': [], 'missing_skills': []}
    dept, role, skills = found
    text = role_text(dept, role, skills)
    role_words = _words(text)
    coverage = len(role_words & _words(resume_text)) / max(1, len(role_words))

    resume_low = (resume_text or '').lower()
    ok = coverage >= MIN_COVERAGE and all(
        re.search(needs, resume_low) for title_pat, needs in FUNCTION_TERMS if re.search(title_pat, role.lower()))
    topics, _source = role_bank_topics(dept, role, skills)
    role_ind = topic_industries(topics)
    matching, missing = split_role_skills(resume_text, skills)
    return {
        'known': True,
        # What this role needs that the resume does / does not show — shown on
        # the result page instead of the resume-only skill lists.
        'matching_skills': matching,
        'missing_skills': missing,
        'ok': ok,
        'coverage': round(coverage * 100),
        # The interview's domain questions are drawn from these topics, within
        # these industries. No topics = the bank does not cover this role, and
        # the interview follows the resume instead (resume_utils._domain_inputs).
        'topics': topics,
        'industries': role_ind,
        'text': text,
    }
