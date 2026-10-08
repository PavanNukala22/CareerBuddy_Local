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
