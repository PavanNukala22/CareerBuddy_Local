"""Free plan Skill Up lock. Run: python manage.py test core.test_skillup_access"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.skillup_access import is_locked_lesson

User = get_user_model()
BASE = '/static/001%20Career%20Buddy/'
TECH = BASE + 'TechCenter/development/python-developer/01_language_typing.html'
VOCAB = BASE + 'Vocabulary/phonics-03-blends-digraphs.html'


class SkillUpAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('su', 'su@x.com', 'pw12345!')

    def _paid(self):
        p = self.user.profile
        p.plan_type, p.is_pro = 'normal', False
        p.subscription_start = timezone.now() - timedelta(days=1)
        p.save()

    def test_which_lessons_are_locked(self):
        self.assertTrue(is_locked_lesson(TECH))
        self.assertTrue(is_locked_lesson(BASE + 'AptitudeReasoning/Questions/003%20verbal_ability_guide.html'))
        self.assertTrue(is_locked_lesson(BASE + 'NonITCenter/non-technical/payroll-workforce-administration-support/01_payroll_implementation_specialist.html'))
        self.assertFalse(is_locked_lesson(VOCAB))
        self.assertFalse(is_locked_lesson(BASE + '001%20CEFR/cefr_a1_english.html'))
        self.assertFalse(is_locked_lesson(BASE + 'GrammerActivities/x.html'))
        self.assertFalse(is_locked_lesson(BASE + 'TechCenter/english_vocab_mock_test.html'))
        self.assertFalse(is_locked_lesson(BASE + 'TechCenter/mock_test.js'))   # assets stay public
        self.assertFalse(is_locked_lesson('/static/js/assessment_popup.js'))

    def test_free_user_refused_locked_lesson(self):
        self.client.force_login(self.user)
        resp = self.client.get(TECH)
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, 'locked', status_code=403)

    def test_anonymous_refused_locked_lesson(self):
        self.assertEqual(self.client.get(TECH).status_code, 403)

    def test_free_user_gets_english_lesson(self):
        self.client.force_login(self.user)
        self.assertNotEqual(self.client.get(VOCAB).status_code, 403)

    def test_paid_user_gets_locked_lesson(self):
        self._paid()
        self.client.force_login(self.user)
        self.assertNotEqual(self.client.get(TECH).status_code, 403)

    def test_quiz_api_locks_non_english_subjects(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/activities/quiz/python/questions/').status_code, 403)
        self.assertNotEqual(self.client.get('/activities/quiz/english/questions/').status_code, 403)
        self._paid()
        self.assertNotEqual(self.client.get('/activities/quiz/python/questions/').status_code, 403)

    def test_buddy_opens_tech_role_course_for_paid_only(self):
        import json
        from riya_bot.riya_assistant import riya_chat_logic, stream_assistant_response
        msg = 'open frontend developer styling tools'
        page = 'frontend-developer/frontend_developer_styling_tools.html'

        def routes(payload):
            return ' '.join(a.get('route', '') for a in payload.get('actions') or [])

        def streamed():
            for chunk in stream_assistant_response(msg, path='/skill-up/', api_key='', user=self.user):
                if chunk.startswith('data:') and '"actions"' in chunk:
                    return json.loads(chunk[5:])
            return {}

        for get in (lambda: riya_chat_logic(msg, path='/skill-up/', api_key='', user=self.user), streamed):
            self.assertNotIn(page, routes(get()))
            self.assertIn('/pro/', routes(get()))
        self._paid()
        for get in (lambda: riya_chat_logic(msg, path='/skill-up/', api_key='', user=self.user), streamed):
            self.assertIn(page, routes(get()))

    def test_buddy_opens_every_kind_of_department_and_role(self):
        from riya_bot.riya_assistant import riya_chat_logic

        def route(msg):
            acts = riya_chat_logic(msg, path='/dashboard/', api_key='', user=self.user).get('actions') or []
            return acts[0]['route'] if len(acts) == 1 else [a['route'] for a in acts]

        cases = {
            'open development department': '/skill-up/#grp-tech-development',
            'open frontend developer': '/skill-up/#role-tech-development--frontend-developer',
            'open epc project workforce solutions': '/skill-up/#grp-nonit-epc-project-workforce-solutions',
            'open lead technical recruiter (engineering)':
                '/skill-up/#role-nonit-engineering-recruitment-technical-staffing--lead-technical-recruiter-engineering',
            'open devops engineer in devops infrastructure': '/skill-up/#role-tech-devops-infrastructure--devops-engineer',
            # short names: every word typed is in one department / role name
            'Open Agile and delivery': '/skill-up/#grp-tech-project-management-agile-delivery',
            'open customer success': '/skill-up/#grp-tech-customer-success-technical-support',
            'open oil and gas': '/skill-up/#grp-nonit-oil-gas-energy-skills',
            'open lead technical recruiter':
                '/skill-up/#role-nonit-engineering-recruitment-technical-staffing--lead-technical-recruiter-engineering',
            'open sde': '/skill-up/#role-tech-development--software-development-engineer-sde',
            'open product owner': '/skill-up/#role-tech-project-management-agile-delivery--product-owner',
        }
        for msg in cases:
            self.assertEqual(route(msg), '/pro/', msg)              # Free plan: plans page
        self.assertEqual(route('open skill up'), '/skill-up/#depth-english')   # Free keeps English
        self._paid()
        for msg, want in cases.items():
            self.assertEqual(route(msg), want, msg)
        both = route('open devops engineer')                      # same role in two departments: ask
        self.assertIn('/skill-up/#role-tech-development--devops-engineer', both)
        self.assertIn('/skill-up/#role-tech-devops-infrastructure--devops-engineer', both)
