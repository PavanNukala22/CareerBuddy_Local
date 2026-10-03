"""Rule-based resume assembly for the manual Resume Builder.

The candidate's form state is normalised, checked against fixed rules and
turned into an ordered resume document (sections only when they have content).
The same document drives the on-page preview and the PDF, so the two always
match. No text is generated or inferred: every line in the output comes from
what the candidate entered or explicitly picked from the predefined lists.
"""
import re
import unicodedata
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .resume_roles import LEVEL_KEYS, LEVEL_LABELS

MAX_TEXT = 300
MAX_LONG_TEXT = 2000
MAX_ITEMS = 15
MAX_BULLETS = 15
MAX_SKILLS = 40

PLACEHOLDER_RE = re.compile(r'\[[^\[\]\n]{1,80}\]')
PHONE_DIGITS_RE = re.compile(r'\d')
PHONE_ALLOWED_RE = re.compile(r'^[0-9+()\-\s./]+$')
MONTH_RE = re.compile(r'^(\d{4})-(\d{2})$')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# Step numbers match the builder's step indicator, so an error can take the
# candidate straight to the right panel.
STEP_PERSONAL, STEP_SKILLS, STEP_EXPERIENCE, STEP_EDUCATION, STEP_SUMMARY = 1, 2, 3, 4, 5


# --------------------------------------------------------------------------- #
#  Normalisation
# --------------------------------------------------------------------------- #

def _clean(value, limit=MAX_TEXT):
    if value is None:
        return ''
    text = unicodedata.normalize('NFC', str(value))
    # Drop control characters except newlines/tabs; collapse runs of spaces.
    text = ''.join(ch for ch in text if ch in '\n\t' or unicodedata.category(ch)[0] != 'C')
    text = text.replace('\t', ' ')
    text = '\n'.join(re.sub(r' {2,}', ' ', line).strip() for line in text.split('\n'))
    return text.strip()[:limit]


def _lines(value, limit=MAX_BULLETS):
    """Text area → list of non-empty lines, bullet markers stripped, de-duplicated."""
    if isinstance(value, (list, tuple)):
        raw = [str(v) for v in value]
    else:
        raw = _clean(value, MAX_LONG_TEXT * 2).split('\n')
    out, seen = [], set()
    for line in raw:
        line = _clean(line)
        line = re.sub(r'^\s*(?:[-*•·▪◦‣]|\d+[.)])\s+', '', line).strip()
        key = line.casefold()
        if line and key not in seen:
            seen.add(key)
            out.append(line)
        if len(out) >= limit:
            break
    return out


def _list(value, limit=MAX_SKILLS):
    if isinstance(value, str):
        value = re.split(r'[,\n;]', value)
    if not isinstance(value, (list, tuple)):
        return []
    out, seen = [], set()
    for item in value:
        item = _clean(item, 80)
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _entries(value, fields, long_fields=(), bool_fields=()):
    if not isinstance(value, list):
        return []
    out = []
    for raw in value[:MAX_ITEMS]:
        if not isinstance(raw, dict):
            continue
        entry = {f: _clean(raw.get(f)) for f in fields}
        for f in long_fields:
            entry[f] = _clean(raw.get(f), MAX_LONG_TEXT)
        for f in bool_fields:
            entry[f] = bool(raw.get(f))
        out.append(entry)
    return out


JOB_FIELDS = ('title', 'company', 'location', 'start', 'end')
PROJECT_FIELDS = ('name', 'context', 'tools', 'start', 'end')
EDU_FIELDS = ('degree', 'institution', 'location', 'year', 'score')
CERT_FIELDS = ('name', 'issuer', 'year')
TRAINING_FIELDS = ('name', 'provider', 'year')


def normalize_state(raw):
    """Coerce an untrusted builder payload into a bounded, well-typed dict."""
    raw = raw if isinstance(raw, dict) else {}
    personal = raw.get('personal') if isinstance(raw.get('personal'), dict) else {}
    skills = raw.get('skills') if isinstance(raw.get('skills'), dict) else {}
    groups = skills.get('groups') if isinstance(skills.get('groups'), dict) else {}
    level = raw.get('level') if raw.get('level') in LEVEL_KEYS else ''
    return {
        'role': _clean(raw.get('role'), 80),
        # Describes a role with no predefined template; custom_role() bounds every value.
        'role_def': raw.get('role_def') if isinstance(raw.get('role_def'), dict) else {},
        'level': level,
        'personal': {
            'name': _clean(personal.get('name'), 100),
            'email': _clean(personal.get('email'), 120),
            'phone': _clean(personal.get('phone'), 40),
            'location': _clean(personal.get('location'), 100),
            'linkedin': _clean(personal.get('linkedin'), 200),
            'website': _clean(personal.get('website'), 200),
            'dob': _clean(personal.get('dob'), 20),
            'passport': _clean(personal.get('passport'), 20).upper(),
        },
        'target_title': _clean(raw.get('target_title'), 100),
        'domain': _clean(raw.get('domain'), 100),
        'years': _clean(raw.get('years'), 10),
        'skills': {
            'groups': {_clean(k, 40): _list(v) for k, v in list(groups.items())[:20]},
            'suggested': _list(skills.get('suggested')),
            'soft': _list(skills.get('soft')),
            'other': _list(skills.get('other')),
        },
        'employment': _entries(raw.get('employment'), JOB_FIELDS, ('bullets',), ('current',)),
        'internships': _entries(raw.get('internships'), JOB_FIELDS, ('bullets',), ('current',)),
        'projects': _entries(raw.get('projects'), PROJECT_FIELDS, ('bullets',)),
        'education': _entries(raw.get('education'), EDU_FIELDS),
        'certifications': _entries(raw.get('certifications'), CERT_FIELDS),
        'training': _entries(raw.get('training'), TRAINING_FIELDS),
        'achievements': _clean(raw.get('achievements'), MAX_LONG_TEXT),
        'languages': _clean(raw.get('languages'), 200),
        'additional': _clean(raw.get('additional'), MAX_LONG_TEXT),
        'summary': _clean(raw.get('summary'), MAX_LONG_TEXT),
        'declaration': bool(raw.get('declaration')),
        'place': _clean(raw.get('place'), 60),
        'decl_date': _clean(raw.get('decl_date'), 20),
    }


# --------------------------------------------------------------------------- #
#  Helpers shared by validation and assembly
# --------------------------------------------------------------------------- #

def _filled(entry, *keys):
    return all(entry.get(k) for k in keys)


def _touched(entry, ignore=('current',)):
    return any(v for k, v in entry.items() if k not in ignore)


def valid_jobs(entries):
    return [e for e in entries if _filled(e, 'title', 'company')]


def valid_projects(entries):
    return [e for e in entries if e.get('name')]


def valid_education(entries):
    return [e for e in entries if e.get('degree')]


def valid_named(entries):
    return [e for e in entries if e.get('name')]


def role_skill_groups(state, role):
    """[(label, [items])] for the role's own fields, in the role's order."""
    groups = state['skills']['groups']
    out, used = [], set()
    for field in (role or {}).get('fields', []):
        items = groups.get(field['key']) or []
        if items:
            out.append((field['label'], items))
        used.add(field['key'])
    # Keys the role no longer defines (e.g. an admin renamed a field) still count.
    for key, items in groups.items():
        if key not in used and items:
            out.append(('Skills', items))
    return out


def relevant_skill_count(state, role):
    seen = set()
    for _, items in role_skill_groups(state, role):
        seen.update(i.casefold() for i in items)
    seen.update(i.casefold() for i in state['skills']['suggested'])
    seen.update(i.casefold() for i in state['skills']['other'])
    return len(seen)


def is_valid_email(value):
    try:
        validate_email(value)
    except ValidationError:
        return False
    return True


def is_valid_phone(value):
    digits = len(PHONE_DIGITS_RE.findall(value or ''))
    return bool(value) and bool(PHONE_ALLOWED_RE.match(value)) and 7 <= digits <= 15


def _month_key(value):
    m = MONTH_RE.match(value or '')
    if not m:
        return None
    year, month = int(m.group(1)), int(m.group(2))
    return (year, month) if 1 <= month <= 12 else None


def format_month(value):
    """'2023-04' → 'Apr 2023'; anything else is shown exactly as typed."""
    key = _month_key(value)
    if key:
        return f'{MONTHS[key[1] - 1]} {key[0]}'
    return value or ''


def date_range(start, end, current=False):
    start_txt = format_month(start)
    end_txt = 'Present' if current else format_month(end)
    if start_txt and end_txt:
        return f'{start_txt} – {end_txt}'
    return start_txt or end_txt


def has_placeholder(text):
    return bool(PLACEHOLDER_RE.search(text or ''))


# --------------------------------------------------------------------------- #
#  Validation
# --------------------------------------------------------------------------- #

def _err(field, step, message):
    return {'field': field, 'step': step, 'message': message}


def validate_state(state, role):
    """Mandatory-field rules. Returns a list of errors; empty means ready.

    Employment history and certifications are never mandatory on their own:
    freshers may use projects, internships or training, and experienced
    candidates may use projects (a warning nudges them to add employment).
    """
    errors = []
    p = state['personal']
    if len(p['name']) < 2:
        errors.append(_err('personal.name', STEP_PERSONAL, 'Please enter your full name.'))
    if not is_valid_email(p['email']):
        errors.append(_err('personal.email', STEP_PERSONAL, 'Please provide a valid email address.'))
    if not is_valid_phone(p['phone']):
        errors.append(_err('personal.phone', STEP_PERSONAL, 'Please enter a valid contact number (7–15 digits).'))
    if p['passport'] and not re.fullmatch(r'[A-Z0-9]{6,12}', p['passport']):
        errors.append(_err('personal.passport', STEP_PERSONAL,
                           'Please enter a valid passport number (6–12 letters or digits).'))
    if re.match(r'^\d{4}-\d{2}-\d{2}$', p['dob'] or '') and p['dob'] >= date.today().isoformat():
        errors.append(_err('personal.dob', STEP_PERSONAL, 'Date of birth must be in the past.'))
    if not role:
        errors.append(_err('role', STEP_SKILLS, 'Please select a job role.'))
    if not state['level']:
        errors.append(_err('level', STEP_SKILLS, 'Please select your experience level.'))
    if state['years'] and not re.fullmatch(r'\d{1,2}(\.\d)?', state['years']):
        errors.append(_err('years', STEP_SKILLS, 'Please enter your years of experience as a number.'))
    if role and relevant_skill_count(state, role) == 0:
        errors.append(_err('skills', STEP_SKILLS, 'Please select relevant skills for your chosen role.'))

    # Partially filled entries would print half a line, so they must be completed or removed.
    for list_key, label in (('employment', 'employment'), ('internships', 'internship')):
        for i, e in enumerate(state[list_key]):
            if _touched(e) and not _filled(e, 'title', 'company'):
                field = 'title' if not e.get('title') else 'company'
                errors.append(_err(f'{list_key}.{i}.{field}', STEP_EXPERIENCE,
                                   f'Please complete the role title and organisation for {label} {i + 1}, or remove it.'))
    for i, e in enumerate(state['projects']):
        if _touched(e) and not e.get('name'):
            errors.append(_err(f'projects.{i}.name', STEP_EXPERIENCE,
                               f'Please add a name for project {i + 1}, or remove it.'))
    for list_key in ('employment', 'internships', 'projects'):
        for i, e in enumerate(state[list_key]):
            start, end = _month_key(e.get('start')), _month_key(e.get('end'))
            if start and end and not e.get('current') and end < start:
                errors.append(_err(f'{list_key}.{i}.end', STEP_EXPERIENCE, 'End date cannot be before the start date.'))
            if start and start > (date.today().year, date.today().month):
                errors.append(_err(f'{list_key}.{i}.start', STEP_EXPERIENCE, 'Start date cannot be in the future.'))

    jobs = valid_jobs(state['employment'])
    projects = valid_projects(state['projects'])
    if state['level'] == 'fresher':
        has_experience = jobs or projects or valid_jobs(state['internships']) or valid_named(state['training'])
    else:
        has_experience = jobs or projects
    if not has_experience:
        errors.append(_err('employment', STEP_EXPERIENCE, 'Please provide your employment details or relevant projects.'))

    for i, e in enumerate(state['education']):
        if _touched(e) and not e.get('degree'):
            errors.append(_err(f'education.{i}.degree', STEP_EDUCATION,
                               f'Please enter the degree or qualification for education entry {i + 1}, or remove it.'))
    if not valid_education(state['education']):
        errors.append(_err('education', STEP_EDUCATION, 'Please add your education details.'))
    for i, e in enumerate(state['certifications']):
        if _touched(e) and not e.get('name'):
            errors.append(_err(f'certifications.{i}.name', STEP_EDUCATION,
                               f'Please add the certification name for entry {i + 1}, or remove it.'))
    for i, e in enumerate(state['training']):
        if _touched(e) and not e.get('name'):
            errors.append(_err(f'training.{i}.name', STEP_EDUCATION,
                               f'Please add the training name for entry {i + 1}, or remove it.'))

    # Template text must be replaced with the candidate's own facts before it is printed.
    if has_placeholder(state['summary']):
        errors.append(_err('summary', STEP_SUMMARY,
                           'Please replace the [placeholder] text in your professional summary with your own details.'))
    if has_placeholder(state['achievements']):
        errors.append(_err('achievements', STEP_SUMMARY,
                           'Please replace the [placeholder] text in your achievements with your own details.'))
    for list_key in ('employment', 'internships', 'projects'):
        for i, e in enumerate(state[list_key]):
            if has_placeholder(e.get('bullets')):
                errors.append(_err(f'{list_key}.{i}.bullets', STEP_EXPERIENCE,
                                   'Please replace the [placeholder] text in your responsibilities with your own details.'))
    return errors


def warnings_for(state, role):
    """Non-blocking suggestions shown next to the preview."""
    warnings = []
    if not state['summary']:
        warnings.append('Add a short professional summary — pick a template and edit it to match your background.')
    if state['level'] in ('1-3', '3-5', '5+') and not valid_jobs(state['employment']):
        warnings.append('Add your employment history to support an experienced-level resume.')
    if relevant_skill_count(state, role) and relevant_skill_count(state, role) < 5:
        warnings.append('Consider selecting a few more relevant skills (5 or more reads well to recruiters).')
    if not state['personal']['location']:
        warnings.append('Adding your city helps recruiters filter by location.')
    return warnings


def completeness(state, role):
    """Per-category progress for the completeness indicator (0–100 each)."""
    p = state['personal']
    personal = sum(bool(x) for x in (len(p['name']) >= 2, is_valid_email(p['email']),
                                     is_valid_phone(p['phone']), p['location'])) / 4
    career_checks = [bool(role), bool(state['level']), bool(state['target_title'] or role),
                     bool(state['summary']) and not has_placeholder(state['summary'])]
    if state['level'] in ('1-3', '3-5', '5+'):
        career_checks.append(bool(state['years']))
    career = sum(career_checks) / len(career_checks)
    education = 1.0 if valid_education(state['education']) else 0.0
    skills = min(relevant_skill_count(state, role), 5) / 5 if role else 0.0
    jobs = valid_jobs(state['employment'])
    other_exp = valid_projects(state['projects']) or valid_jobs(state['internships']) or valid_named(state['training'])
    if state['level'] == 'fresher':
        experience = 1.0 if (jobs or other_exp) else 0.0
    else:
        experience = 1.0 if jobs else (0.5 if valid_projects(state['projects']) else 0.0)
    extras = 1.0 if (valid_named(state['certifications']) or _lines(state['achievements'])) else 0.0
    categories = [
        {'key': 'personal', 'label': 'Personal Information', 'value': personal, 'optional': False, 'step': STEP_PERSONAL},
        {'key': 'career', 'label': 'Career Information', 'value': career, 'optional': False, 'step': STEP_SKILLS},
        {'key': 'education', 'label': 'Education', 'value': education, 'optional': False, 'step': STEP_EDUCATION},
        {'key': 'skills', 'label': 'Skills', 'value': skills, 'optional': False, 'step': STEP_SKILLS},
        {'key': 'experience', 'label': 'Experience or Projects', 'value': experience, 'optional': False, 'step': STEP_EXPERIENCE},
        {'key': 'extras', 'label': 'Certifications or Achievements', 'value': extras, 'optional': True, 'step': STEP_EDUCATION},
    ]
    for c in categories:
        c['value'] = round(c['value'] * 100)
    overall = round(sum(c['value'] for c in categories) / len(categories))
    return {'overall': overall, 'categories': categories}


# --------------------------------------------------------------------------- #
#  Document assembly
# --------------------------------------------------------------------------- #

def _months_between(start, end, current=False):
    """Inclusive month count, e.g. Aug 2025 – Jan 2026 → 6. None when dates are not YYYY-MM."""
    s = _month_key(start)
    e = (date.today().year, date.today().month) if current else _month_key(end)
    if not s or not e or e < s:
        return None
    return (e[0] - s[0]) * 12 + (e[1] - s[1]) + 1


def format_duration(months):
    if not months:
        return ''
    years, rem = divmod(months, 12)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if rem:
        parts.append(f"{rem} month{'s' if rem > 1 else ''}")
    return ' '.join(parts)


def _job_items(entries):
    items = []
    for e in valid_jobs(entries):
        items.append({
            'title': e['title'],
            'subtitle': e['company'],
            'location': e['location'],
            'dates': date_range(e['start'], e['end'], e.get('current')),
            'duration': format_duration(_months_between(e['start'], e['end'], e.get('current'))),
            'bullets': _lines(e.get('bullets')),
        })
    return items


def _dedupe_skills(groups):
    """Drop a skill that already appeared in an earlier group (case-insensitive)."""
    seen, out = set(), []
    for label, items in groups:
        kept = [i for i in items if i.casefold() not in seen]
        seen.update(i.casefold() for i in kept)
        if kept:
            out.append({'label': label, 'items': kept})
    return out


def format_dob(value):
    """'2002-04-18' (date input) → '18-04-2002'; anything else as typed."""
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', value or '')
    return f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else (value or '')


DECLARATION_TEXT = ('I hereby declare that the information provided above is true and accurate to the best of '
                    'my knowledge and belief.')


def build_document(state, role):
    """Ordered resume sections built only from the candidate's own entries.

    Layout and order follow CareerBuddy's reference resume: summary, work
    experience, skills, projects, certifications, education, declaration.
    Freshers keep Education and Projects ahead of any employment. Empty
    sections are omitted.
    """
    p = state['personal']
    title = state['target_title'] or (role or {}).get('title', '')
    contact = []
    if p['phone']:
        digits = re.sub(r'[^\d+]', '', p['phone'])
        contact.append({'text': p['phone'], 'href': f'tel:{digits}' if digits else ''})
    if p['email']:
        contact.append({'text': p['email'], 'href': f"mailto:{p['email']}" if is_valid_email(p['email']) else ''})
    for key in ('linkedin', 'website'):
        url = p[key]
        if url:
            href = url if re.match(r'^https?://', url, re.I) else f'https://{url}'
            shown = re.sub(r'^https?://(www\.)?', '', url, flags=re.I).rstrip('/')
            contact.append({'text': shown, 'href': href if re.match(r'^https?://[^\s<>"]+$', href) else ''})
    if p['dob']:
        contact.append({'text': f"D.O.B : {format_dob(p['dob'])}", 'href': ''})
    if p['passport']:
        contact.append({'text': f"Passport No : {p['passport']}", 'href': ''})
    if p['location']:
        contact.append({'text': p['location'], 'href': ''})

    sections = {}
    if state['summary']:
        sections['summary'] = {'heading': 'Professional Summary', 'kind': 'text', 'text': state['summary']}

    jobs = _job_items(state['employment'])
    if jobs:
        label = (role or {}).get('experience_label') or 'Work Experience'
        if label == 'Professional Experience':
            label = 'Work Experience'
        sections['experience'] = {'heading': label, 'kind': 'jobs', 'items': jobs}

    # Title-case labels for the skills table ("Programming Languages"), keeping acronyms as written.
    skill_groups = [(' '.join(w[:1].upper() + w[1:] for w in label.split(' ')), items)
                    for label, items in role_skill_groups(state, role)]
    if state['skills']['suggested']:
        skill_groups.append(('Additional Skills', state['skills']['suggested']))
    if state['skills']['other']:
        skill_groups.append(('Other Skills', state['skills']['other']))
    if state['skills']['soft']:
        skill_groups.append(('Professional Skills', state['skills']['soft']))
    skill_groups = _dedupe_skills(skill_groups)
    if skill_groups:
        heading = 'Technical Skills' if (role or {}).get('category') in ('it', 'tech') else 'Key Skills'
        sections['skills'] = {'heading': heading, 'kind': 'skills', 'groups': skill_groups}

    projects = [{
        'title': e['name'],
        'subtitle': e['context'],
        'dates': date_range(e['start'], e['end']),
        'bullets': _lines(e.get('bullets')),
        'tech': e['tools'],
    } for e in valid_projects(state['projects'])]
    if projects:
        sections['projects'] = {'heading': 'Projects', 'kind': 'projects', 'items': projects}

    interns = _job_items(state['internships'])
    if interns:
        sections['internships'] = {'heading': 'Internships', 'kind': 'jobs', 'items': interns}

    achievements = _lines(state['achievements'])
    if achievements:
        sections['achievements'] = {'heading': 'Achievements', 'kind': 'bullets', 'items': achievements}

    certs, trainings = valid_named(state['certifications']), valid_named(state['training'])
    credentials = [{'title': e['name'], 'subtitle': e['issuer'], 'dates': e['year']} for e in certs]
    credentials += [{'title': e['name'], 'subtitle': e['provider'], 'dates': e['year']} for e in trainings]
    if credentials:
        heading = ('Certifications & Training' if certs and trainings
                   else 'Certifications' if certs else 'Training')
        sections['credentials'] = {'heading': heading, 'kind': 'compact', 'items': credentials}

    education = []
    for e in valid_education(state['education']):
        meta = ' | '.join(x for x in (e['institution'], e['location'], e['year'], e['score']) if x)
        education.append({'title': e['degree'], 'meta': meta})
    if education:
        sections['education'] = {'heading': 'Education', 'kind': 'education', 'items': education}

    additional = []
    if state['languages']:
        additional.append(f"Languages: {state['languages']}")
    additional.extend(_lines(state['additional']))
    if additional:
        sections['additional'] = {'heading': 'Additional Information', 'kind': 'bullets', 'items': additional}

    if state['declaration']:
        when = state['decl_date']
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', when or '')
        when = f'{m.group(3)}/{m.group(2)}/{m.group(1)}' if m else (when or date.today().strftime('%d/%m/%Y'))
        sections['declaration'] = {
            'heading': 'Declaration', 'kind': 'declaration', 'text': DECLARATION_TEXT,
            'place': state['place'] or p['location'].split(',')[0].strip(),
            'date': when, 'name': p['name'],
        }

    if state['level'] == 'fresher':
        order = ('summary', 'education', 'skills', 'projects', 'internships', 'experience',
                 'achievements', 'credentials', 'additional', 'declaration')
    else:
        order = ('summary', 'experience', 'skills', 'projects', 'internships', 'achievements',
                 'credentials', 'education', 'additional', 'declaration')

    return {
        'name': p['name'],
        'title': title,
        'contact': contact,
        'level': state['level'],
        'level_label': LEVEL_LABELS.get(state['level'], ''),
        'role': (role or {}).get('title', ''),
        'sections': [dict(sections[key], key=key) for key in order if key in sections],
    }


def resume_filename(state, role):
    """e.g. 'Raghuvaran_Reddy_Project_Manager_Resume.pdf' (ASCII-safe)."""
    def part(text):
        ascii_text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
        return re.sub(r'[^A-Za-z0-9]+', '_', ascii_text).strip('_')
    name = part(state['personal']['name']) or 'Candidate'
    title = part((role or {}).get('title') or state['target_title']) or 'Resume'
    return f'{name}_{title}_Resume.pdf'
