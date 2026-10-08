"""Tests for the Create Resume builder (manual, multi-template, PDF, drafts)."""
import io
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .create_resume import build_document, normalize, resume_filename, validate
from .models import ResumeDraft


def personal(**kw):
    p = {'name': 'Raghuvaran Reddy', 'title': 'Project Manager', 'email': 'raghu@example.com',
         'phone': '+91 98765 43210', 'city': 'Hyderabad', 'state': 'Telangana', 'country': 'India'}
    p.update(kw)
    return p


def state(**kw):
    s = {'personal': personal(), 'summary': 'Project manager with six years of delivery experience.'}
    s.update(kw)
    return s


def fields(errors):
    return {e['field'] for e in errors}


JOB_OLD = {'company': 'Older Co', 'title': 'Site Engineer', 'start_month': '6', 'start_year': '2018',
           'end_month': '3', 'end_year': '2021', 'responsibilities': 'Supervised daily site work for a crew of 20'}
JOB_NOW = {'company': 'ABC Infra', 'title': 'Project Manager', 'type': 'Full-time', 'start_month': '4',
           'start_year': '2021', 'current': True, 'responsibilities': '- Led 12 engineers\nControlled budgets',
           'achievements': 'Delivered the tower two weeks early', 'tools': 'MS Project'}


class ValidationTests(TestCase):
    def test_complete_minimum_is_valid(self):
        self.assertEqual(validate(normalize(state())), [])

    def test_required_personal_fields(self):
        errors = validate(normalize({}))
        for f in ('name', 'title', 'email', 'phone', 'city', 'state', 'country'):
            self.assertIn(f'personal.{f}', fields(errors))

    def test_email_phone_and_url_formats(self):
        errors = validate(normalize(state(personal=personal(email='x@', phone='12', linkedin='not a url',
                                                            github='github.com/me', portfolio='https://me.dev'))))
        self.assertTrue({'personal.email', 'personal.phone'} <= fields(errors))
        self.assertFalse({'personal.linkedin', 'personal.github', 'personal.portfolio'} & fields(errors))   # URLs never block

    def test_optional_sections_are_never_required(self):
        # No experience, education, skills or projects: a fresher may download.
        self.assertEqual(validate(normalize(state(summary=''))), [])

    def test_partial_entries_and_date_ranges(self):
        errors = validate(normalize(state(
            experience=[{'company': 'X', 'start_year': '2022', 'end_year': '2020'}],
            projects=[{'overview': 'no title'}],
            certifications=[{'name': 'PMP', 'issue_year': '2023', 'exp_year': '2021'}],
            languages=[{'proficiency': 'Native', 'name': ''}, {'name': 'Hindi'}])))
        f = fields(errors)
        self.assertTrue({'experience.0.title', 'experience.0.end_year', 'projects.0.title',
                         'certifications.0.issuer', 'certifications.0.exp_year'} <= f)
        self.assertNotIn('languages.0.name', f)        # an untouched row is simply ignored

    def test_future_start_rejected_current_allowed(self):
        errors = validate(normalize(state(experience=[dict(JOB_NOW, start_year='2999')])))
        self.assertIn('experience.0.start_year', fields(errors))
        self.assertEqual(validate(normalize(state(experience=[JOB_NOW]))), [])

    def test_untrusted_values_are_bounded(self):
        s = normalize({'template': 'evil', 'summary': 'x' * 5000, 'experience': [{'type': 'Hacker'}] * 50,
                       'skills': {'technical': ['A'] * 100}})
        self.assertEqual(s['template'], 'classic')
        self.assertEqual(len(s['summary']), 1200)
        self.assertEqual(len(s['experience']), 20)
        self.assertEqual(s['experience'][0]['type'], '')
        self.assertEqual(s['skills']['technical'], ['A'])     # de-duplicated


class FieldRuleTests(TestCase):
    def errs(self, **kw):
        return {e['field']: e['message'] for e in validate(normalize(state(**kw)))}

    def test_personal_lengths(self):
        e = self.errs(personal=personal(name='A', title='x' * 101, city='H', address='short'))
        self.assertTrue({'personal.name', 'personal.title', 'personal.city', 'personal.address'} <= set(e))
        self.assertEqual(self.errs(personal=personal(name='x' * 80, address='12 MG Road, Hyderabad')), {})

    def test_phone_counts_digits_only(self):
        for ok in ('+91 98765 43210', '9876543210', '(040) 2345-6789'):
            self.assertNotIn('personal.phone', self.errs(personal=personal(phone=ok)), ok)
        for bad in ('98765 4321', '98765abc43210', '+91 98765 43210 12345', '9876+543210'):
            self.assertIn('personal.phone', self.errs(personal=personal(phone=bad)), bad)
        self.assertEqual(self.errs(personal=personal(phone='12345'))['personal.phone'],
                         'Enter a valid phone number with at least 10 digits.')

    def test_email_rules(self):
        for bad in ('a b@x.com', 'a@x', 'a@@x.com', 'a@' + 'x' * 250 + '.com'):
            self.assertIn('personal.email', self.errs(personal=personal(email=bad)), bad)

    def test_urls_are_not_validated(self):
        for value in ('www.linkedin.com/in/name', 'linkedin.com/name', 'anything', 'javascript:alert(1)'):
            self.assertEqual(self.errs(personal=personal(linkedin=value),
                                       projects=[{'title': 'Tracker', 'url': value}]), {}, value)

    def test_url_links_are_safe(self):
        links = build_document(normalize(state(personal=personal(
            linkedin='www.linkedin.com/in/name', github='javascript:alert(1)', website='https://a b.com'))))['links']
        self.assertEqual([l['href'] for l in links], ['https://www.linkedin.com/in/name'])

    def test_summary_optional_but_meaningful(self):
        self.assertEqual(self.errs(summary=''), {})
        self.assertEqual(self.errs(summary='Good developer')['summary'],
                         'Professional summary should contain at least 50 characters.')

    def test_entry_field_limits_and_bullets(self):
        job = dict(JOB_NOW, responsibilities='Too short', location='x' * 101,
                   achievements='\n'.join(f'Achievement number {i}' for i in range(16)))
        e = self.errs(experience=[job])
        self.assertTrue({'experience.0.responsibilities', 'experience.0.location', 'experience.0.achievements'} <= set(e))

    def test_end_date_required_unless_current(self):
        e = self.errs(experience=[dict(JOB_OLD, end_year='', end_month='')],
                      internships=[{'organization': 'XYZ', 'title': 'Intern', 'start_year': '2020'}])
        self.assertIn('experience.0.end_year', e)
        self.assertIn('internships.0.end_year', e)
        self.assertIn('internships.0.start_year', self.errs(internships=[{'organization': 'XYZ', 'title': 'Intern'}]))
        self.assertNotIn('experience.0.end_year', self.errs(experience=[JOB_NOW]))

    def test_optional_entry_fields_empty_ok(self):
        self.assertEqual(self.errs(education=[{'qualification': 'Diploma', 'institution': 'JNTU'}],
                                   certifications=[{'name': 'PMP', 'issuer': 'PMI'}]), {})

    def test_graduation_before_start(self):
        e = self.errs(education=[{'qualification': 'Diploma', 'institution': 'JNTU', 'start_year': '2020', 'end_year': '2018'}])
        self.assertIn('education.0.end_year', e)

    def test_skills_per_item(self):
        e = self.errs(skills={'technical': ['C', 'Python'], 'soft': [f'Skill {i}' for i in range(31)]})
        self.assertIn('skills.technical', e)
        self.assertIn('skills.soft', e)
        self.assertEqual(normalize({'skills': {'tools': ' Excel , excel,, Jira '}})['skills']['tools'], ['Excel', 'Jira'])

    def test_languages_need_proficiency_and_no_duplicates(self):
        e = self.errs(languages=[{'name': 'English', 'proficiency': 'Native'}, {'name': 'english', 'proficiency': 'Basic'},
                                 {'name': 'Hindi'}])
        self.assertIn('languages.1.name', e)
        self.assertIn('languages.2.proficiency', e)

    def test_additional_limits(self):
        e = self.errs(additional={'hobbies': 'x' * 501, 'publications': 'Paper'})
        self.assertTrue({'additional.hobbies', 'additional.publications'} <= set(e))

    def test_invalid_urls_never_linked(self):
        doc = build_document(normalize(state(projects=[{'title': 'Tracker', 'url': 'javascript:alert(1)'}])))
        self.assertIsNone(doc['sections'][1]['items'][0]['link'])


class DocumentTests(TestCase):
    def keys(self, **kw):
        return [s['key'] for s in build_document(normalize(state(**kw)))['sections']]

    def test_experienced_order_and_newest_first(self):
        doc = build_document(normalize(state(experience=[JOB_OLD, JOB_NOW], skills={'technical': ['AutoCAD']},
                                             education=[{'qualification': "Bachelor's Degree", 'institution': 'JNTU'}])))
        self.assertEqual([s['key'] for s in doc['sections']], ['summary', 'skills', 'experience', 'education'])
        jobs = doc['sections'][2]['items']
        self.assertEqual([j['subtitle'] for j in jobs], ['ABC Infra', 'Older Co'])
        self.assertIn('Apr 2021 – Present', jobs[0]['meta'])
        self.assertEqual(jobs[0]['bullets'], ['Led 12 engineers', 'Controlled budgets'])

    def test_manual_order_is_respected(self):
        doc = build_document(normalize(state(experience=[JOB_OLD, JOB_NOW], order={'experience': 'manual'})))
        self.assertEqual([j['subtitle'] for j in doc['sections'][1]['items']], ['Older Co', 'ABC Infra'])

    def test_fresher_leads_with_education(self):
        keys = self.keys(education=[{'qualification': "Bachelor's Degree", 'institution': 'JNTU'}],
                         projects=[{'title': 'Tracker'}], skills={'soft': ['Teamwork']})
        self.assertEqual(keys, ['summary', 'education', 'skills', 'projects'])

    def test_empty_sections_omitted_and_nothing_invented(self):
        doc = build_document(normalize(state(summary='', languages=[{'name': ''}], additional={'hobbies': ''})))
        self.assertEqual(doc['sections'], [])
        self.assertEqual(doc['name'], 'Raghuvaran Reddy')

    def test_all_sections_render(self):
        s = normalize(state(
            experience=[JOB_NOW], skills={'technical': ['Python'], 'functional': ['Budgeting'], 'soft': ['Leadership'], 'tools': ['Excel']},
            projects=[{'title': 'Tracker', 'type': 'Personal Project', 'url': 'https://github.com/x/y', 'technologies': 'Django', 'outcomes': 'Used on two live construction sites'}],
            education=[{'qualification': "Bachelor's Degree", 'degree': 'B.Tech', 'specialization': 'Civil', 'institution': 'JNTU',
                        'start_year': '2022', 'end_year': '2026', 'current': True}],
            certifications=[{'name': 'PMP', 'issuer': 'PMI', 'issue_year': '2022', 'url': 'https://pmi.org'}],
            achievements=[{'title': 'Best Project', 'year': '2023'}],
            internships=[{'organization': 'XYZ', 'title': 'Intern', 'start_year': '2020', 'end_year': '2020'}], volunteering=[{'organization': 'NGO', 'role': 'Volunteer'}],
            languages=[{'name': 'English', 'proficiency': 'Professional'}], additional={'memberships': 'Member, Institution of Engineers'}))
        doc = build_document(s)
        keys = [x['key'] for x in doc['sections']]
        for k in ('summary', 'skills', 'experience', 'projects', 'internships', 'education', 'certifications',
                  'achievements', 'volunteering', 'additional'):
            self.assertIn(k, keys)
        edu = next(x for x in doc['sections'] if x['key'] == 'education')['items'][0]
        self.assertEqual(edu['title'], 'B.Tech in Civil')
        self.assertIn('2022 – 2026 (Expected)', edu['meta'])

    def test_filename(self):
        self.assertEqual(resume_filename(normalize(state())), 'Raghuvaran_Reddy_Project_Manager_Resume.pdf')


class EndpointTests(TestCase):
    def post(self, name, data, client=None):
        return (client or self.client).post(reverse(name), data=json.dumps(data), content_type='application/json')

    def test_preview_returns_document_even_when_incomplete(self):
        res = self.post('create_resume_preview', {'personal': {'name': 'A'}})
        body = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(body['errors'])
        self.assertEqual(body['status']['personal'], 'error')

    def test_pdf_in_every_template(self):
        from pypdf import PdfReader
        for template in ('classic', 'modern', 'minimal'):
            with self.subTest(template=template):
                res = self.post('create_resume_pdf', state(template=template, experience=[JOB_NOW],
                                personal=personal(name='Zoë Ñandú', linkedin='https://linkedin.com/in/zoe'),
                                summary='Résumé with “quotes” – and ₹. Project manager with six years of delivery.'))
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res['Content-Type'], 'application/pdf')
                self.assertIn('Zoe_Nandu_Project_Manager_Resume.pdf', res['Content-Disposition'])
                reader = PdfReader(io.BytesIO(res.content))
                box = reader.pages[0].mediabox
                self.assertEqual((round(float(box.width)), round(float(box.height))), (595, 842))   # A4
                text = ''.join(p.extract_text() for p in reader.pages)
                self.assertIn('Ñandú'.upper() if template == 'classic' else 'Ñandú', text)
                self.assertIn('“quotes”', text)
                uris = [a.get_object().get('/A', {}).get('/URI') for p in reader.pages for a in p.get('/Annots') or []]
                self.assertIn('mailto:raghu@example.com', uris)
                self.assertIn('https://linkedin.com/in/zoe', uris)

    def test_long_resume_multiple_pages_nothing_lost(self):
        from pypdf import PdfReader
        jobs = [dict(JOB_OLD, company=f'Company {i}', responsibilities='\n'.join(
            f'Responsibility {i}.{j} with enough words to wrap across the whole line of the page' for j in range(10)))
            for i in range(8)]
        res = self.post('create_resume_pdf', state(experience=jobs))
        reader = PdfReader(io.BytesIO(res.content))
        self.assertGreater(len(reader.pages), 1)
        text = ''.join(p.extract_text() for p in reader.pages)
        self.assertIn('Responsibility 7.9', text)

    def test_pdf_rejects_invalid_and_pages_render(self):
        self.assertEqual(self.post('create_resume_pdf', {'personal': {}}).status_code, 400)
        res = self.post('create_resume_pages', state())
        self.assertEqual(res.json()['total'], 1)

    def test_print_inline(self):
        res = self.client.post(reverse('create_resume_pdf'), {'payload': json.dumps(state()), 'inline': '1'})
        self.assertTrue(res['Content-Disposition'].startswith('inline;'))

    def test_csrf_enforced(self):
        res = self.post('create_resume_pdf', state(), client=Client(enforce_csrf_checks=True))
        self.assertEqual(res.status_code, 403)

    def test_landing_has_builder_without_sample_data(self):
        html = self.client.get('/').content.decode()
        self.assertIn('id="crApp"', html)
        self.assertIn('js/create_resume.js', html)
        self.assertNotIn('value="Priya Sharma"', html)


class DraftTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user('alice', 'alice@example.com', 'pw-alice-123')
        self.bob = User.objects.create_user('bob', 'bob@example.com', 'pw-bob-123')
        self.a, self.b = Client(), Client()
        self.a.force_login(self.alice)
        self.b.force_login(self.bob)

    def save(self, client, data, draft_id=None):
        return client.post(reverse('create_resume_draft_save'), data=json.dumps({'id': draft_id, 'data': data}),
                           content_type='application/json')

    def test_anonymous_cannot_use_drafts(self):
        self.assertEqual(self.client.get(reverse('create_resume_drafts')).status_code, 401)
        self.assertEqual(self.save(self.client, state()).status_code, 401)

    def test_save_load_update_delete_own_drafts(self):
        res = self.save(self.a, state(template='modern'))
        draft_id = res.json()['draft']['id']
        self.assertEqual(res.json()['draft']['title'], 'Project Manager – Raghuvaran Reddy')
        self.save(self.a, state(personal=personal(title='Site Engineer')), draft_id)
        self.save(self.a, state(personal=personal(title='Planner')))
        listing = self.a.get(reverse('create_resume_drafts')).json()['drafts']
        self.assertEqual(len(listing), 2)
        loaded = self.a.get(reverse('create_resume_draft', args=[draft_id])).json()
        self.assertEqual(loaded['data']['personal']['title'], 'Site Engineer')
        self.assertEqual(self.a.post(reverse('create_resume_draft_delete', args=[draft_id])).status_code, 200)
        self.assertEqual(ResumeDraft.objects.filter(user=self.alice).count(), 1)

    def test_users_never_see_each_others_resumes(self):
        draft_id = self.save(self.a, state()).json()['draft']['id']
        self.assertEqual(self.b.get(reverse('create_resume_drafts')).json()['drafts'], [])
        self.assertEqual(self.b.get(reverse('create_resume_draft', args=[draft_id])).status_code, 404)
        self.assertEqual(self.save(self.b, state(personal=personal(name='Bob'))
                                   , draft_id).status_code, 404)
        self.assertEqual(self.b.post(reverse('create_resume_draft_delete', args=[draft_id])).status_code, 404)
        self.assertEqual(ResumeDraft.objects.get(pk=draft_id).data['personal']['name'], 'Raghuvaran Reddy')

    def test_draft_limit(self):
        for _ in range(ResumeDraft.MAX_PER_USER):
            self.save(self.a, state())
        self.assertEqual(self.save(self.a, state()).status_code, 400)
