"""Tests for the manual (rule-based, no-AI) Resume Builder."""
import io
import json

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .models import ResumeRoleTemplate
from .resume_document import (build_document, completeness, normalize_state, resume_filename, validate_state,
                              warnings_for)
from .resume_roles import LEVEL_KEYS, client_payload, get_role, get_roles


def base_state(**overrides):
    state = {
        'role': 'project-manager',
        'level': 'fresher',
        'personal': {'name': 'Raghuvaran Reddy', 'email': 'raghu@example.com', 'phone': '+91 98765 43210',
                     'location': 'Hyderabad', 'linkedin': 'linkedin.com/in/raghu', 'website': ''},
        'skills': {'groups': {'project-planning': ['Scheduling', 'Work breakdown structure (WBS)']},
                   'suggested': ['MS Project Basics'], 'soft': ['Teamwork'], 'other': 'Excel'},
        'projects': [{'name': 'Construction schedule for a G+4 building', 'context': 'Academic project',
                      'bullets': 'Prepared the WBS\nBuilt a 12-month schedule'}],
        'education': [{'degree': 'B.Tech, Civil Engineering', 'institution': 'JNTU Hyderabad', 'year': '2024'}],
        'summary': 'Entry-level project management candidate.',
    }
    state.update(overrides)
    return state


def fields(errors):
    return {e['field'] for e in errors}


class RoleDataTests(TestCase):
    def test_every_role_has_complete_predefined_data(self):
        roles = get_roles()
        self.assertGreaterEqual(len(roles), 36)
        self.assertEqual({r['category'] for r in roles}, {'it', 'tech', 'nt'})
        for role in roles:
            with self.subTest(role=role['slug']):
                self.assertTrue(role['description'] and role['responsibilities'] and role['required_skills'])
                self.assertTrue(role['career_path'] and role['industry'])
                self.assertGreaterEqual(len(role['fields']), 4)
                for level in LEVEL_KEYS:
                    self.assertTrue(role['levels'][level]['skills'])
                    self.assertTrue(role['levels'][level]['responsibilities'])
                    self.assertTrue(role['summaries'][level])
                self.assertTrue(role['levels']['fresher']['projects'])

    def test_spec_example_roles_and_fields(self):
        expected = {
            'project-manager': ['Project planning', 'MS Project / Primavera', 'Budgeting and cost control',
                                'Risk management', 'Team leadership', 'Stakeholder communication'],
            'hr-executive': ['Recruitment', 'Employee onboarding', 'HR operations', 'Employee engagement',
                             'Payroll knowledge', 'HR software'],
            'hse-engineer': ['Risk assessment', 'Safety inspections', 'Incident reporting',
                             'Permit-to-work systems', 'Safety audits'],
            'software-developer': ['Programming languages', 'Frontend technologies', 'Backend technologies',
                                   'Databases', 'Frameworks'],
        }
        for slug, labels in expected.items():
            role = get_role(slug)
            got = [f['label'] for f in role['fields']]
            for label in labels:
                self.assertIn(label, got, f'{slug}: {label}')
        self.assertEqual(get_role('hse-engineer')['experience_label'], 'Site Experience')

    def test_fresher_project_manager_suggestions_and_summary(self):
        role = get_role('project-manager')
        for skill in ('Project Planning Fundamentals', 'MS Project Basics', 'Task Coordination',
                      'Risk Identification', 'Teamwork', 'Communication'):
            self.assertIn(skill, role['levels']['fresher']['skills'])
        self.assertEqual(
            role['summaries']['fresher'][0],
            'Motivated entry-level Project Manager candidate with an academic foundation in project planning, '
            'scheduling and team coordination. Interested in applying project management knowledge, '
            'problem-solving and communication skills to support successful project delivery.')
        # Experienced templates leave placeholders for the candidate instead of inventing experience.
        self.assertIn('[X] years', role['summaries']['1-3'][0])
        self.assertIn('[verified skills]', role['summaries']['5+'][0])

    def test_embedded_payload_is_light(self):
        light = json.dumps(client_payload())
        self.assertLess(len(light), 80_000)
        self.assertNotIn('"levels": {"fresher"', light)


class ValidationTests(TestCase):
    def setUp(self):
        self.role = get_role('project-manager')

    def check(self, **overrides):
        state = normalize_state(base_state(**overrides))
        return validate_state(state, self.role), state

    def test_complete_fresher_is_valid(self):
        errors, _ = self.check()
        self.assertEqual(errors, [])

    def test_mandatory_messages(self):
        errors = validate_state(normalize_state({}), None)
        messages = {e['message'] for e in errors}
        for msg in ('Please enter your full name.', 'Please provide a valid email address.',
                    'Please select your experience level.', 'Please add your education details.',
                    'Please provide your employment details or relevant projects.', 'Please select a job role.'):
            self.assertIn(msg, messages)

    def test_invalid_email_and_phone(self):
        errors, _ = self.check(personal={'name': 'A B', 'email': 'bad@', 'phone': '12'})
        self.assertTrue({'personal.email', 'personal.phone'} <= fields(errors))

    def test_skills_required(self):
        errors, _ = self.check(skills={'soft': ['Teamwork']})
        self.assertIn('skills', fields(errors))

    def test_fresher_may_use_internship_or_training_instead_of_employment(self):
        errors, _ = self.check(projects=[], internships=[{'title': 'Intern', 'company': 'ABC'}])
        self.assertEqual(errors, [])
        errors, _ = self.check(projects=[], training=[{'name': 'Primavera P6 course'}])
        self.assertEqual(errors, [])

    def test_experienced_needs_employment_or_projects_but_never_certifications(self):
        errors, _ = self.check(level='3-5', projects=[])
        self.assertIn('employment', fields(errors))
        errors, state = self.check(level='3-5')           # projects only: allowed, with a warning
        self.assertEqual(errors, [])
        self.assertTrue(any('employment history' in w for w in warnings_for(state, self.role)))

    def test_partial_entries_and_dates(self):
        errors, _ = self.check(employment=[{'title': 'Engineer', 'start': '2023-05', 'end': '2022-01'}])
        self.assertIn('employment.0.company', fields(errors))
        self.assertIn('employment.0.end', fields(errors))

    def test_placeholders_must_be_replaced(self):
        errors, _ = self.check(summary='Project Manager with [X] years of experience.',
                               achievements='Reduced [errors] by 10%')
        self.assertTrue({'summary', 'achievements'} <= fields(errors))

    def test_completeness_categories(self):
        _, state = self.check()
        result = completeness(state, self.role)
        self.assertEqual(len(result['categories']), 6)
        self.assertTrue(result['categories'][-1]['optional'])
        self.assertGreater(result['overall'], 50)


class DocumentTests(TestCase):
    def setUp(self):
        self.role = get_role('project-manager')

    def keys(self, **overrides):
        return [s['key'] for s in build_document(normalize_state(base_state(**overrides)), self.role)['sections']]

    def test_fresher_order_puts_education_and_projects_first(self):
        self.assertEqual(self.keys(), ['summary', 'education', 'skills', 'projects'])

    def test_experienced_order_emphasises_experience(self):
        keys = self.keys(level='5+', achievements='Delivered two projects on schedule',
                         employment=[{'title': 'Project Manager', 'company': 'ABC', 'start': '2019-01', 'current': True}])
        # Reference-resume order: experience, skills, projects, achievements, education.
        self.assertEqual(keys, ['summary', 'experience', 'skills', 'projects', 'achievements', 'education'])

    def test_empty_sections_omitted_and_no_invented_text(self):
        doc = build_document(normalize_state(base_state(summary='')), self.role)
        self.assertNotIn('summary', [s['key'] for s in doc['sections']])
        text = json.dumps(doc)
        for invented in ('Motivated', 'applied to', 'Eager to contribute'):
            self.assertNotIn(invented, text)

    def test_skills_deduplicated_and_dates_formatted(self):
        state = normalize_state(base_state(
            level='1-3', skills={'groups': {'project-planning': ['Scheduling']}, 'suggested': ['scheduling', 'Budget Control']},
            employment=[{'title': 'Planner', 'company': 'XYZ', 'start': '2022-03', 'current': True, 'bullets': '- Built schedules'}]))
        doc = build_document(state, self.role)
        skills = next(s for s in doc['sections'] if s['key'] == 'skills')
        flat = [i.lower() for g in skills['groups'] for i in g['items']]
        self.assertEqual(flat.count('scheduling'), 1)
        job = next(s for s in doc['sections'] if s['key'] == 'experience')['items'][0]
        self.assertEqual(job['dates'], 'Mar 2022 – Present')
        self.assertEqual(job['bullets'], ['Built schedules'])

    def test_reference_layout_fields(self):
        state = normalize_state(base_state(
            level='1-3', personal={'name': 'Raghuvaran Reddy Y', 'email': 'r@example.com', 'phone': '9876543210',
                                   'location': 'Hyderabad, India', 'dob': '2002-04-18', 'passport': 'y1234567'},
            employment=[{'title': 'Associate Software Engineer', 'company': 'Royal International Staffing',
                         'start': '2025-08', 'end': '2026-01'}],
            projects=[{'name': 'Kraftudio Portal', 'tools': 'React, Django', 'bullets': '**Built** dashboards'}],
            declaration=True, decl_date='2026-07-01'))
        self.assertEqual(validate_state(state, self.role), [])
        doc = build_document(state, self.role)
        contact = [c['text'] for c in doc['contact']]
        self.assertIn('D.O.B : 18-04-2002', contact)
        self.assertIn('Passport No : Y1234567', contact)
        job = next(s for s in doc['sections'] if s['key'] == 'experience')
        self.assertEqual(job['heading'], 'Work Experience')
        self.assertEqual(job['items'][0]['duration'], '6 months')
        project = next(s for s in doc['sections'] if s['key'] == 'projects')['items'][0]
        self.assertEqual(project['tech'], 'React, Django')
        decl = doc['sections'][-1]
        self.assertEqual((decl['kind'], decl['place'], decl['date']), ('declaration', 'Hyderabad', '01/07/2026'))

    def test_invalid_passport_and_future_dob(self):
        state = normalize_state(base_state(personal={'name': 'A B', 'email': 'a@example.com', 'phone': '9876543210',
                                                     'passport': 'x!', 'dob': '2999-01-01'}))
        self.assertTrue({'personal.passport', 'personal.dob'} <= fields(validate_state(state, self.role)))

    def test_filename(self):
        state = normalize_state(base_state(personal={'name': 'Raghuvaran Reddy'}))
        self.assertEqual(resume_filename(state, self.role), 'Raghuvaran_Reddy_Project_Manager_Resume.pdf')
        state = normalize_state(base_state(personal={'name': 'José Ñúñez'}))
        self.assertEqual(resume_filename(state, self.role), 'Jose_Nunez_Project_Manager_Resume.pdf')


class EndpointTests(TestCase):
    def post(self, name, data, **kwargs):
        return self.client.post(reverse(name), data=json.dumps(data), content_type='application/json', **kwargs)

    def test_preview_returns_document(self):
        res = self.post('manual_resume_preview', base_state())
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['document']['name'], 'Raghuvaran Reddy')
        self.assertEqual(body['filename'], 'Raghuvaran_Reddy_Project_Manager_Resume.pdf')

    def test_preview_rejects_missing_information(self):
        res = self.post('manual_resume_preview', base_state(education=[]))
        self.assertEqual(res.status_code, 400)
        self.assertIn('Please add your education details.', [e['message'] for e in res.json()['errors']])

    def test_pdf_download_is_a_real_pdf(self):
        from pypdf import PdfReader
        state = base_state(personal={'name': 'Zoë Ñandú', 'email': 'zoe@example.com', 'phone': '9876543210',
                                     'linkedin': 'linkedin.com/in/zoe'},
                           summary='Résumé with “smart quotes”, an en dash – and ₹ symbol.')
        res = self.post('manual_resume_pdf', state)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="Zoe_Nandu_Project_Manager_Resume.pdf"', res['Content-Disposition'])
        self.assertTrue(res.content.startswith(b'%PDF-'))
        reader = PdfReader(io.BytesIO(res.content))
        text = ''.join(p.extract_text() for p in reader.pages)
        for fragment in ('ZOË ÑANDÚ', 'PROFESSIONAL SUMMARY', 'Construction schedule', 'B.Tech, Civil Engineering'):
            self.assertIn(fragment, text)
        self.assertIn('“smart quotes”', text)
        uris = [a.get_object().get('/A', {}).get('/URI') for p in reader.pages for a in p.get('/Annots') or []]
        self.assertIn('mailto:zoe@example.com', uris)
        self.assertIn('https://linkedin.com/in/zoe', uris)

    def test_long_resume_spans_multiple_pages(self):
        from pypdf import PdfReader
        jobs = [{'title': f'Engineer {i}', 'company': f'Company {i}', 'start': '2015-01', 'end': '2016-01',
                 'bullets': '\n'.join(f'Responsibility {i}.{j} with enough words to wrap across the line width'
                                      for j in range(8))} for i in range(8)]
        res = self.post('manual_resume_pdf', base_state(level='5+', employment=jobs))
        reader = PdfReader(io.BytesIO(res.content))
        self.assertGreater(len(reader.pages), 1)
        text = ''.join(p.extract_text() for p in reader.pages)
        self.assertIn('Responsibility 7.7', text)          # nothing lost at the end

    def test_print_posts_form_payload_inline(self):
        res = self.client.post(reverse('manual_resume_pdf'), {'payload': json.dumps(base_state()), 'inline': '1'})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res['Content-Disposition'].startswith('inline;'))
        bad = self.client.post(reverse('manual_resume_pdf'), {'payload': '{}', 'inline': '1'})
        self.assertEqual(bad.status_code, 400)
        self.assertIn('Please enter your full name.', bad.content.decode())

    def test_page_images(self):
        res = self.post('manual_resume_pages', base_state())
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['total'], 1)
        self.assertTrue(body['pages'][0].startswith('data:image/png;base64,'))

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        res = client.post(reverse('manual_resume_pdf'), data=json.dumps(base_state()), content_type='application/json')
        self.assertEqual(res.status_code, 403)

    def test_bad_payloads(self):
        res = self.client.post(reverse('manual_resume_preview'), data='not json', content_type='application/json')
        self.assertEqual(res.status_code, 400)
        res = self.client.get(reverse('manual_resume_pdf'))
        self.assertEqual(res.status_code, 405)

    def test_roles_api(self):
        res = self.client.get(reverse('manual_resume_roles'), {'slug': 'hse-engineer'})
        self.assertEqual(res.json()['role']['title'], 'HSE Engineer')
        self.assertEqual(self.client.get(reverse('manual_resume_roles'), {'slug': 'nope'}).status_code, 404)

    def test_landing_page_embeds_roles_and_builder(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        self.assertIn('id="cb-resume-data"', html)
        self.assertIn('id="rbForm"', html)
        self.assertIn('Choose Your Path', html)
        self.assertNotIn('application/msword', html)


class AdminOverrideTests(TestCase):
    def test_override_add_and_hide_roles(self):
        ResumeRoleTemplate.objects.create(slug='project-manager', title='Project Manager', category='tech',
                                          description='Custom description', responsibilities='One\nTwo')
        ResumeRoleTemplate.objects.create(
            slug='safety-officer', title='Safety Officer', category='tech', industry='Construction',
            role_fields=[{'label': 'Inspections', 'options': ['Daily checks']}],
            level_suggestions={'fresher': {'skills': ['Hazard spotting'], 'responsibilities': ['Assisted audits']}})
        ResumeRoleTemplate.objects.create(slug='web-designer', title='Web Designer', category='it', is_active=False)
        pm = get_role('project-manager')
        self.assertEqual(pm['description'], 'Custom description')
        self.assertEqual(pm['responsibilities'], ['One', 'Two'])
        self.assertTrue(pm['fields'])                       # untouched fields keep the defaults
        new = get_role('safety-officer')
        self.assertEqual(new['fields'][0]['label'], 'Inspections')
        self.assertIn('Safety Officer', new['summaries']['fresher'][0])
        self.assertIsNone(get_role('web-designer'))

    def test_seed_command(self):
        call_command('seed_resume_roles', stdout=io.StringIO())
        self.assertEqual(ResumeRoleTemplate.objects.count(), 36)
        self.assertEqual(get_role('hse-engineer')['fields'][0]['label'], 'Risk assessment')
