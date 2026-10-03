"""Create Resume module: a fully manual resume builder (no AI, no suggestions).

Candidates type every word of their resume. This module only:
  * normalises the posted form state (types, lengths, list sizes),
  * validates it with fixed rules (required fields, email / phone / URL
    formats, date ranges),
  * arranges the entered content into ATS-friendly sections in a standard
    order, omitting anything left empty.

The same document dict drives the live preview and the PDF
(``create_resume_pdf``), so the two always contain the same content. Nothing
is invented, suggested or rewritten.
"""
import re
import unicodedata
from datetime import date

from .resume_document import _clean, _lines, _list, is_valid_email, is_valid_phone

TEMPLATES = ('classic', 'modern', 'minimal')
EMPLOYMENT_TYPES = ('Full-time', 'Part-time', 'Internship', 'Contract', 'Freelance', 'Apprenticeship', 'Other')
QUALIFICATIONS = ('PhD', "Master's Degree", "Bachelor's Degree", 'Diploma', 'Higher Secondary', 'Secondary School', 'Other')
PROJECT_TYPES = ('Academic Project', 'Personal Project', 'Professional Project', 'Internship Project',
                 'Research Project', 'Other')
PROFICIENCY = ('Basic', 'Conversational', 'Intermediate', 'Professional', 'Native')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
SKILL_CATEGORIES = (('technical', 'Technical Skills'), ('functional', 'Functional Skills'),
                    ('soft', 'Soft Skills'), ('tools', 'Tools & Technologies'))
ADDITIONAL_FIELDS = (('memberships', 'Professional Memberships'), ('publications', 'Publications'),
                     ('research', 'Research'), ('activities', 'Extracurricular Activities'),
                     ('hobbies', 'Hobbies & Interests'), ('other', 'Other Information'))
SECTIONS = ('personal', 'summary', 'experience', 'education', 'skills', 'projects', 'certifications',
            'achievements', 'internships', 'languages')
REPEATABLE = ('experience', 'education', 'projects', 'certifications', 'achievements', 'internships',
              'volunteering', 'languages')

SUMMARY_LIMIT = 1200
MAX_ENTRIES = 20
URL_RE = re.compile(r'^(https?://)?([\w-]+\.)+[a-z]{2,}(:\d+)?(/[^\s<>"]*)?$', re.I)

PERSONAL_FIELDS = ('name', 'title', 'email', 'phone', 'city', 'state', 'country', 'linkedin', 'github',
                   'portfolio', 'website', 'profile_url', 'address')
URL_FIELDS = (('linkedin', 'LinkedIn'), ('github', 'GitHub'), ('portfolio', 'Portfolio'),
              ('website', 'Website'), ('profile_url', 'Profile'))
DATE_FIELDS = ('start_month', 'start_year', 'end_month', 'end_year')
ENTRY_FIELDS = {
    'experience': (('company', 'title', 'type', 'location', 'department', 'tools') + DATE_FIELDS,
                   ('responsibilities', 'projects', 'achievements'), ('current',)),
    'education': (('qualification', 'degree', 'specialization', 'institution', 'location', 'start_year',
                   'end_year', 'grade', 'coursework'), ('achievements',), ('current',)),
    'projects': (('title', 'type', 'organization', 'role', 'technologies', 'url') + DATE_FIELDS,
                 ('overview', 'responsibilities', 'outcomes'), ('current',)),
    'certifications': (('name', 'issuer', 'issue_month', 'issue_year', 'exp_month', 'exp_year',
                        'credential_id', 'url'), ('description',), ()),
    'achievements': (('title', 'organization', 'month', 'year', 'url'), ('description',), ()),
    'internships': (('organization', 'title', 'location', 'skills') + DATE_FIELDS,
                    ('responsibilities', 'projects', 'achievements'), ('current',)),
    'volunteering': (('organization', 'role', 'location') + DATE_FIELDS,
                     ('responsibilities', 'contributions', 'achievements'), ('current',)),
    'languages': (('name', 'proficiency'), (), ()),
}
# Fields that make an entry meaningful; an entry that has content but lacks
# these must be completed or removed before the PDF is generated.
ENTRY_REQUIRED = {
    'experience': (('company', 'Company name'), ('title', 'Job title'), ('start_year', 'Start year')),
    'education': (('qualification', 'Qualification'), ('institution', 'Institution')),
    'projects': (('title', 'Project title'),),
    'certifications': (('name', 'Certification name'), ('issuer', 'Issuing organisation')),
    'achievements': (('title', 'Achievement title'),),
    'internships': (('organization', 'Organisation'), ('title', 'Internship title')),
    'volunteering': (('organization', 'Organisation'), ('role', 'Role')),
    'languages': (('name', 'Language'),),
}
SECTION_OF = {'volunteering': 'internships'}   # volunteering lives in the Internships & Volunteering step


# --------------------------------------------------------------------------- #
#  Normalisation
# --------------------------------------------------------------------------- #

def _year(value):
    value = _clean(value, 4)
    return value if re.fullmatch(r'(19|20)\d{2}', value) else ''


def _month(value):
    value = _clean(value, 2)
    return str(int(value)) if value.isdigit() and 1 <= int(value) <= 12 else ''


def _entry(raw, kind):
    short, long_, flags = ENTRY_FIELDS[kind]
    raw = raw if isinstance(raw, dict) else {}
    entry = {}
    for f in short:
        if f.endswith('_year') or f == 'year':
            entry[f] = _year(raw.get(f))
        elif f.endswith('_month') or f == 'month':
            entry[f] = _month(raw.get(f))
        else:
            entry[f] = _clean(raw.get(f), 200 if f != 'url' else 300)
    for f in long_:
        entry[f] = _clean(raw.get(f), 2000)
    for f in flags:
        entry[f] = bool(raw.get(f))
    if kind == 'experience' and entry['type'] not in EMPLOYMENT_TYPES:
        entry['type'] = ''
    if kind == 'education' and entry['qualification'] not in QUALIFICATIONS:
        entry['qualification'] = ''
    if kind == 'projects' and entry['type'] not in PROJECT_TYPES:
        entry['type'] = ''
    if kind == 'languages' and entry['proficiency'] not in PROFICIENCY:
        entry['proficiency'] = ''
    return entry


def normalize(raw):
    """Coerce an untrusted builder payload into a bounded, well-typed dict."""
    raw = raw if isinstance(raw, dict) else {}
    personal = raw.get('personal') if isinstance(raw.get('personal'), dict) else {}
    skills = raw.get('skills') if isinstance(raw.get('skills'), dict) else {}
    additional = raw.get('additional') if isinstance(raw.get('additional'), dict) else {}
    order = raw.get('order') if isinstance(raw.get('order'), dict) else {}
    state = {
        'template': raw.get('template') if raw.get('template') in TEMPLATES else 'classic',
        'personal': {f: _clean(personal.get(f), 300 if f in dict(URL_FIELDS) else 160) for f in PERSONAL_FIELDS},
        'summary': _clean(raw.get('summary'), SUMMARY_LIMIT),
        'skills': {key: _list(skills.get(key), 40) for key, _ in SKILL_CATEGORIES},
        'additional': {key: _clean(additional.get(key), 2000) for key, _ in ADDITIONAL_FIELDS},
        'order': {k: ('manual' if order.get(k) == 'manual' else 'auto') for k in REPEATABLE},
    }
    for kind in REPEATABLE:
        items = raw.get(kind) if isinstance(raw.get(kind), list) else []
        state[kind] = [_entry(item, kind) for item in items[:MAX_ENTRIES]]
    return state


# --------------------------------------------------------------------------- #
#  Validation
# --------------------------------------------------------------------------- #

def _err(field, section, message):
    return {'field': field, 'section': section, 'message': message}


def is_valid_url(value):
    return bool(URL_RE.match(value or ''))


def _ym(year, month, end=False):
    if not year:
        return None
    return (int(year), int(month) if month else (12 if end else 1))


def _touched(entry):
    return any(v for k, v in entry.items() if k not in ('current', 'proficiency', 'type', 'qualification'))


def validate(state):
    """Fixed rules only. Returns a list of errors; empty means ready to download."""
    errors = []
    p = state['personal']
    required = (('name', 'Please enter your full name.'), ('title', 'Please enter your professional title or target role.'),
                ('city', 'Please enter your current city.'), ('state', 'Please enter your state.'),
                ('country', 'Please enter your country.'))
    for field, message in required[:2]:
        if len(p[field]) < 2:
            errors.append(_err(f'personal.{field}', 'personal', message))
    if not is_valid_email(p['email']):
        errors.append(_err('personal.email', 'personal', 'Please enter a valid email address.'))
    if not is_valid_phone(p['phone']):
        errors.append(_err('personal.phone', 'personal', 'Please enter a valid contact number (7–15 digits).'))
    for field, message in required[2:]:
        if not p[field]:
            errors.append(_err(f'personal.{field}', 'personal', message))
    for field, label in URL_FIELDS:
        if p[field] and not is_valid_url(p[field]):
            errors.append(_err(f'personal.{field}', 'personal', f'Please enter a valid {label} URL.'))

    today = (date.today().year, date.today().month)
    for kind in REPEATABLE:
        section = SECTION_OF.get(kind, kind)
        for i, e in enumerate(state[kind]):
            if not _touched(e):
                continue
            for field, label in ENTRY_REQUIRED[kind]:
                if not e.get(field):
                    errors.append(_err(f'{kind}.{i}.{field}', section,
                                       f'{label} is required for {kind.rstrip("s")} entry {i + 1} (or remove the entry).'))
            if e.get('url') and not is_valid_url(e['url']):
                errors.append(_err(f'{kind}.{i}.url', section, 'Please enter a valid URL.'))
            if 'start_year' in e:
                start = _ym(e['start_year'], e.get('start_month'))
                end = None if e.get('current') else _ym(e.get('end_year'), e.get('end_month'), end=True)
                if start and end and end < start:
                    errors.append(_err(f'{kind}.{i}.end_year', section, 'End date cannot be before the start date.'))
                if start and start > today:
                    errors.append(_err(f'{kind}.{i}.start_year', section, 'Start date cannot be in the future.'))
                if kind != 'education' and end and end > today:
                    errors.append(_err(f'{kind}.{i}.end_year', section,
                                       'End date is in the future — tick "Currently" if this is ongoing.'))
            if kind == 'certifications':
                issued, expires = _ym(e['issue_year'], e['issue_month']), _ym(e['exp_year'], e['exp_month'], end=True)
                if issued and issued > today:
                    errors.append(_err(f'certifications.{i}.issue_year', section, 'Issue date cannot be in the future.'))
                if issued and expires and expires < issued:
                    errors.append(_err(f'certifications.{i}.exp_year', section, 'Expiry date cannot be before the issue date.'))
            if kind == 'achievements' and _ym(e['year'], e['month']) and _ym(e['year'], e['month']) > today:
                errors.append(_err(f'achievements.{i}.year', section, 'Date cannot be in the future.'))
    return errors


def section_status(state, errors):
    """Per form section: 'complete', 'partial', 'empty' or 'error' (drives the progress indicator)."""
    bad = {e['section'] for e in errors}
    p = state['personal']
    filled = {
        'personal': all(p[f] for f in ('name', 'title', 'email', 'phone', 'city', 'state', 'country')),
        'summary': bool(state['summary']),
        'skills': any(state['skills'].values()),
        'languages': bool(state['languages']) or any(state['additional'].values()),
        'internships': bool(state['internships'] or state['volunteering']),
    }
    out = {}
    for s in SECTIONS:
        has = filled.get(s, bool(state.get(s)))
        out[s] = 'error' if s in bad else ('complete' if has else 'empty')
    return out


# --------------------------------------------------------------------------- #
#  Document assembly
# --------------------------------------------------------------------------- #

def fmt_month_year(month, year):
    if not year:
        return ''
    return f'{MONTHS[int(month) - 1]} {year}' if month else year


def date_span(e, current_label='Present'):
    start = fmt_month_year(e.get('start_month'), e.get('start_year'))
    end = current_label if e.get('current') else fmt_month_year(e.get('end_month'), e.get('end_year'))
    if start and end:
        return f'{start} – {end}'
    return start or end


def _sort_key(e):
    """Newest first: ongoing entries, then by end date, then by start date."""
    end = _ym(e.get('end_year') or e.get('issue_year') or e.get('year'),
              e.get('end_month') or e.get('issue_month') or e.get('month'), end=True) or (0, 0)
    start = _ym(e.get('start_year'), e.get('start_month')) or (0, 0)
    return (1 if e.get('current') else 0, end, start)


def _ordered(state, kind, entries):
    if state['order'].get(kind) == 'manual':
        return entries
    return sorted(entries, key=_sort_key, reverse=True)


def _href(url):
    if not url:
        return ''
    href = url if re.match(r'^https?://', url, re.I) else f'https://{url}'
    return href if re.match(r'^https?://[^\s<>"]+$', href) else ''


def _shown_url(url):
    return re.sub(r'^https?://(www\.)?', '', url or '', flags=re.I).rstrip('/')


def _complete(kind, entries):
    return [e for e in entries if all(e.get(f) for f, _ in ENTRY_REQUIRED[kind])]


def build_document(state):
    """Ordered, ATS-friendly sections built only from what the candidate entered."""
    p = state['personal']
    contact = []
    if p['email']:
        contact.append({'text': p['email'], 'href': f"mailto:{p['email']}" if is_valid_email(p['email']) else ''})
    if p['phone']:
        contact.append({'text': p['phone'], 'href': ''})
    place = ', '.join(x for x in (p['city'], p['state'], p['country']) if x)
    if place:
        contact.append({'text': place, 'href': ''})
    links = []
    for field, _label in URL_FIELDS:
        if p[field] and is_valid_url(p[field]):
            links.append({'text': _shown_url(p[field]), 'href': _href(p[field])})

    sections = {}
    if state['summary']:
        sections['summary'] = {'heading': 'Professional Summary', 'kind': 'text', 'text': state['summary']}

    skill_lines = [{'label': label, 'text': ', '.join(state['skills'][key])}
                   for key, label in SKILL_CATEGORIES if state['skills'][key]]
    if skill_lines:
        sections['skills'] = {'heading': 'Skills', 'kind': 'lines', 'items': skill_lines}

    def job_items(kind, title_key, org_key, groups):
        items = []
        for e in _ordered(state, kind, _complete(kind, state[kind])):
            meta = ' | '.join(x for x in (e.get('type'), e.get('location'), e.get('department'), date_span(e)) if x)
            item = {'title': e[title_key], 'subtitle': e[org_key], 'meta': meta,
                    'bullets': _lines(e.get('responsibilities')), 'groups': [], 'notes': []}
            for key, label in groups:
                values = _lines(e.get(key))
                if values:
                    item['groups'].append({'label': label, 'bullets': values})
            tools = e.get('tools') or e.get('skills')
            if tools:
                item['notes'].append({'label': 'Tools & Technologies', 'text': tools})
            items.append(item)
        return items

    experience = job_items('experience', 'title', 'company',
                           (('projects', 'Projects Handled'), ('achievements', 'Key Achievements')))
    if experience:
        sections['experience'] = {'heading': 'Professional Experience', 'kind': 'entries', 'items': experience}

    internships = job_items('internships', 'title', 'organization',
                            (('projects', 'Projects'), ('achievements', 'Achievements')))
    if internships:
        sections['internships'] = {'heading': 'Internships', 'kind': 'entries', 'items': internships}

    volunteering = []
    for e in _ordered(state, 'volunteering', _complete('volunteering', state['volunteering'])):
        item = {'title': e['role'], 'subtitle': e['organization'],
                'meta': ' | '.join(x for x in (e.get('location'), date_span(e)) if x),
                'bullets': _lines(e.get('responsibilities')), 'groups': [], 'notes': []}
        for key, label in (('contributions', 'Contributions'), ('achievements', 'Achievements')):
            if _lines(e.get(key)):
                item['groups'].append({'label': label, 'bullets': _lines(e[key])})
        volunteering.append(item)
    if volunteering:
        sections['volunteering'] = {'heading': 'Volunteering', 'kind': 'entries', 'items': volunteering}

    projects = []
    for e in _ordered(state, 'projects', _complete('projects', state['projects'])):
        item = {'title': e['title'], 'subtitle': e.get('type'),
                'meta': ' | '.join(x for x in (e.get('organization'), date_span(e, 'Ongoing')) if x),
                'link': {'text': _shown_url(e['url']), 'href': _href(e['url'])} if e.get('url') else None,
                'paragraphs': [x for x in (e.get('overview') or '').split('\n') if x.strip()],
                'bullets': _lines(e.get('responsibilities')), 'groups': [], 'notes': []}
        if e.get('role'):
            item['notes'].insert(0, {'label': 'Role', 'text': e['role']})
        if _lines(e.get('outcomes')):
            item['groups'].append({'label': 'Outcomes', 'bullets': _lines(e['outcomes'])})
        if e.get('technologies'):
            item['notes'].append({'label': 'Technologies', 'text': e['technologies']})
        projects.append(item)
    if projects:
        sections['projects'] = {'heading': 'Projects', 'kind': 'entries', 'items': projects}

    education = []
    for e in _ordered(state, 'education', _complete('education', state['education'])):
        title = e.get('degree') or e['qualification']
        if e.get('specialization'):
            title = f"{title} in {e['specialization']}" if e.get('degree') else f"{title} – {e['specialization']}"
        span = ''
        if e.get('start_year') or e.get('end_year'):
            end = 'Present' if e.get('current') and not e.get('end_year') else e.get('end_year')
            if e.get('current') and e.get('end_year'):
                end = f"{e['end_year']} (Expected)"
            span = ' – '.join(x for x in (e.get('start_year'), end) if x)
        item = {'title': title, 'subtitle': '',
                'meta': ' | '.join(x for x in (e['institution'], e.get('location'), span, e.get('grade')) if x),
                'bullets': [], 'groups': [], 'notes': []}
        if e.get('coursework'):
            item['notes'].append({'label': 'Relevant Coursework', 'text': e['coursework']})
        if _lines(e.get('achievements')):
            item['groups'].append({'label': 'Academic Achievements', 'bullets': _lines(e['achievements'])})
        education.append(item)
    if education:
        sections['education'] = {'heading': 'Education', 'kind': 'entries', 'items': education}

    certs = []
    for e in _ordered(state, 'certifications', _complete('certifications', state['certifications'])):
        parts = [e['issuer']]
        if e.get('issue_year'):
            parts.append(f"Issued {fmt_month_year(e['issue_month'], e['issue_year'])}")
        if e.get('exp_year'):
            parts.append(f"Expires {fmt_month_year(e['exp_month'], e['exp_year'])}")
        if e.get('credential_id'):
            parts.append(f"Credential ID: {e['credential_id']}")
        certs.append({'title': e['name'], 'text': ' | '.join(parts),
                      'detail': e.get('description') or '',
                      'link': {'text': 'Verify credential', 'href': _href(e['url'])} if e.get('url') else None})
    if certs:
        sections['certifications'] = {'heading': 'Certifications & Training', 'kind': 'items', 'items': certs}

    achievements = []
    for e in _ordered(state, 'achievements', _complete('achievements', state['achievements'])):
        meta = ' | '.join(x for x in (e.get('organization'), fmt_month_year(e.get('month'), e.get('year'))) if x)
        achievements.append({'title': e['title'], 'text': meta, 'detail': e.get('description') or '',
                             'link': {'text': _shown_url(e['url']), 'href': _href(e['url'])} if e.get('url') else None})
    if achievements:
        sections['achievements'] = {'heading': 'Achievements & Awards', 'kind': 'items', 'items': achievements}

    languages = [f"{e['name']} ({e['proficiency']})" if e.get('proficiency') else e['name']
                 for e in state['languages'] if e.get('name')]
    extra = []
    if languages:
        extra.append({'label': 'Languages', 'text': ', '.join(languages)})
    for key, label in ADDITIONAL_FIELDS:
        values = _lines(state['additional'][key])
        if values:
            extra.append({'label': label, 'text': '; '.join(values)})
    if extra:
        sections['additional'] = {'heading': 'Additional Information', 'kind': 'lines', 'items': extra}

    if experience:
        order = ('summary', 'skills', 'experience', 'projects', 'internships', 'education', 'certifications',
                 'achievements', 'volunteering', 'additional')
    else:   # no professional experience yet: education and projects lead
        order = ('summary', 'education', 'skills', 'internships', 'projects', 'certifications', 'achievements',
                 'volunteering', 'additional')
    return {
        'template': state['template'],
        'name': p['name'],
        'title': p['title'],
        'contact': contact,
        'links': links,
        'address': p['address'],
        'sections': [dict(sections[k], key=k) for k in order if k in sections],
    }


def resume_filename(state):
    """CandidateName_TargetRole_Resume.pdf (ASCII-safe)."""
    def part(text):
        ascii_text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
        return re.sub(r'[^A-Za-z0-9]+', '_', ascii_text).strip('_')
    name = part(state['personal']['name']) or 'Candidate'
    role = part(state['personal']['title'])
    return f'{name}_{role}_Resume.pdf' if role else f'{name}_Resume.pdf'


def draft_title(state):
    p = state['personal']
    return (' – '.join(x for x in (p['title'], p['name']) if x) or 'Untitled resume')[:120]
