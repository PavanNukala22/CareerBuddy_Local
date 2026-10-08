"""Resume Parsing plan gates: Free gets 4 analyses, the AI Interview needs an
ATS score of 90+, and a below-90 interview links to the chosen role's Skill Up
content. Run: python manage.py test career_app.test_resume_plan_gates"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from career_app.models import JobDescription, Resume, ResumeInterviewSession

User = get_user_model()


def _set_plan(user, plan):
    p = user.profile
    p.plan_type = plan
    p.is_pro = (plan == 'pro')
    p.subscription_start = timezone.now() - timedelta(days=1)
    p.save()


class ResumePlanGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('gate', 'gate@x.com', 'pw12345!')
        self.client.force_login(self.user)

    def test_free_plan_stops_after_four_analyses(self):
        for _ in range(4):
            JobDescription.objects.create(user=self.user, text='General Resume Analysis')
        with mock.patch('career_app.views.analyze_resume_with_sarvam') as analyze:
            resp = self.client.post(reverse('resume_job_match'), {'text': ''})
        analyze.assert_not_called()
        self.assertContains(resp, 'You have used all 4 Resume Parsing analyses')

    def test_paid_plan_has_no_parse_limit(self):
        _set_plan(self.user, 'normal')
        for _ in range(6):
            JobDescription.objects.create(user=self.user, text='General Resume Analysis')
        resp = self.client.post(reverse('resume_job_match'), {'text': ''})
        self.assertContains(resp, 'Please upload a resume.')

    def _start_with_ats(self, score):
        resume = Resume.objects.create(user=self.user, extracted_text='Python developer, 2 years experience.')
        jd = JobDescription.objects.create(user=self.user, text='General Resume Analysis')
        s = self.client.session
        s['rb_resume_id'], s['rb_jd_id'] = resume.id, jd.id
        s['rb_analysis'] = {'match_percentage': score, 'matching_skills': ['python']}
        s.save()
        return self.client.get(reverse('resume_start_interview'))

    def test_interview_locked_below_90_ats(self):
        _set_plan(self.user, 'pro')
        resp = self._start_with_ats(89)
        self.assertRedirects(resp, reverse('resume_job_match'), fetch_redirect_response=False)
        self.assertFalse(ResumeInterviewSession.objects.exists())

    def test_interview_opens_at_90_ats(self):
        _set_plan(self.user, 'pro')
        resp = self._start_with_ats(90)
        self.assertRedirects(resp, reverse('resume_interview_chat'), fetch_redirect_response=False)

    def test_free_plan_never_gets_interview(self):
        resp = self._start_with_ats(95)
        self.assertRedirects(resp, reverse('pro_page'), fetch_redirect_response=False)

    def test_failed_interview_links_role_skillup(self):
        _set_plan(self.user, 'normal')
        self.client.get(reverse('resume_builder'), {
            'role': 'Refinery Operations', 'dept': 'Oil & Gas / Energy Skills', 'track': 'nonit'})
        resume = Resume.objects.create(user=self.user, extracted_text='Operator, 2 years experience.')
        jd = JobDescription.objects.create(user=self.user, text='General Resume Analysis')
        session = ResumeInterviewSession.objects.create(resume=resume, job_description=jd)
        s = self.client.session
        s['rb_interview_session_id'] = session.id
        s.save()
        resp = self.client.get(reverse('resume_analytics'))
        self.assertContains(resp, 'Skill up yourself')
        self.assertContains(
            resp, '/skill-up/?section=role-nonit-oil-gas-energy-skills--refinery-operations')


DEV_RESUME = (
    'Software developer. Skills: Python, Java, SQL, PostgreSQL, MySQL, Git, GitHub, Bash, Linux. '
    'Data structures, algorithms, object-oriented programming, unit testing, code reviews, debugging, CI/CD. '
    'Built Django REST APIs. Experience 2022 - 2025. arjun@example.com +91 98765 43210'
)


class RoleFitGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('fit', 'fit@x.com', 'pw12345!')
        self.client.force_login(self.user)
        _set_plan(self.user, 'pro')

    def _start(self, role, dept, track):
        from career_app.role_fit import assess_role_fit
        resume = Resume.objects.create(user=self.user, extracted_text=DEV_RESUME)
        jd = JobDescription.objects.create(user=self.user, text='General Resume Analysis')
        s = self.client.session
        s['rb_resume_id'], s['rb_jd_id'] = resume.id, jd.id
        s['rb_analysis'] = {'match_percentage': 95, 'matching_skills': ['python']}
        s['rb_role'] = {'role': role, 'dept': dept, 'track': track, 'section': 'x'}
        s['rb_role_fit'] = assess_role_fit(DEV_RESUME, track, dept, role)
        s.save()
        return self.client.get(reverse('resume_start_interview'))

    def test_mismatched_role_locks_interview(self):
        resp = self._start('Refinery Operations', 'Oil & Gas / Energy Skills', 'nonit')
        self.assertRedirects(resp, reverse('resume_job_match'), fetch_redirect_response=False)
        self.assertFalse(ResumeInterviewSession.objects.exists())

    def test_matching_role_opens_interview_focused_on_role(self):
        resp = self._start('Software Developer', 'Development', 'tech')
        self.assertRedirects(resp, reverse('resume_interview_chat'), fetch_redirect_response=False)
        session = ResumeInterviewSession.objects.get()
        self.assertEqual(session.target_role['role'], 'Software Developer')
        self.assertIn('Required skills', session.target_role['text'])

    def test_domain_inputs_follow_role(self):
        from career_app.resume_utils import _domain_inputs
        text, skills, _ = _domain_inputs(DEV_RESUME, ['python'], {'text': 'Role text', 'topics': ['t'], 'industries': ['x']})
        self.assertEqual((text, skills), ('Role text', []))
        # A role the question bank does not cover (no topics) follows the resume.
        text, skills, _ = _domain_inputs(DEV_RESUME, ['python'], {'text': 'Role text', 'topics': [], 'industries': []})
        self.assertEqual((text, skills), (DEV_RESUME, ['python']))
        text, skills, _ = _domain_inputs(DEV_RESUME, ['python'], None)
        self.assertEqual((text, skills), (DEV_RESUME, ['python']))


class RoleSkillSplitTests(TestCase):
    def test_missing_skills_come_from_the_role(self):
        from career_app.role_fit import split_role_skills
        role = [
            'Core Languages: Python, Java, C++, or C#',
            'Databases: Relational databases (PostgreSQL, MySQL), basic SQL querying',
            'Computer Science Fundamentals: Data Structures, Algorithms',
            'Testing & Quality: Unit testing, basic CI/CD awareness',
        ]
        have, missing = split_role_skills('Python dev. SQL, PostgreSQL, CI/CD, unit testing. Built sales data reports.', role)
        self.assertEqual(have, ['Python', 'Relational databases (PostgreSQL, MySQL)', 'basic SQL querying',
                                'Unit testing', 'basic CI/CD awareness'])
        # Pick-one line covered by Python; "data" alone is not Data Structures.
        self.assertEqual(missing, ['Data Structures', 'Algorithms'])

    def test_unrelated_resume_misses_every_role_skill(self):
        from career_app.role_fit import split_role_skills
        role = ['Vendor-neutral management', 'VMS administration', 'Supplier performance scorecards']
        have, missing = split_role_skills(DEV_RESUME, role)
        self.assertEqual((have, missing), ([], role))
