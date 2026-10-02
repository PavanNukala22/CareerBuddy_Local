"""AMCAT / CoCubes submit -> grade -> certificate.

Run:  python manage.py test skillup_assessment.tests_mock_submit
"""
import json
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from activities import views as activity_views

_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=_MEDIA)
class MockTestSubmitTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA, ignore_errors=True)

    def _submit(self, name, fraction_correct, user=None):
        bank = {'amcat': activity_views._amcat_bank, 'cocubes': activity_views._cocubes_bank}[name]
        by_id = {q['id']: q for pool in bank().values() for q in pool}
        if user:
            self.client.force_login(user)
        else:
            self.client.logout()
        paper = self.client.get(reverse(f'{name}_questions')).json()
        served = [q for s in paper['sections'] for q in s['questions']]
        k = round(len(served) * fraction_correct)

        # Options are served in a per-user shuffled order and an answer is the
        # DISPLAYED position, so answer the way a candidate does: by finding
        # the correct option's text among the options actually shown.
        def displayed_answer(q, correct):
            bank_q = by_id[q['id']]
            right = bank_q['options'][bank_q['answer']]
            if correct:
                return q['options'].index(right)
            return next(i for i, text in enumerate(q['options']) if text != right)

        answers = {q['id']: displayed_answer(q, n < k) for n, q in enumerate(served)}
        resp = self.client.post(reverse(f'{name}_submit'), data=json.dumps({'answers': answers}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        return resp.json()

    def _user(self, username, full_name=True):
        return User.objects.create_user(username, password='pass12345',
                                        first_name='Asha' if full_name else '',
                                        last_name='Rao' if full_name else '')

    def test_full_score_is_graded_and_certificate_generated(self):
        for name in ('amcat', 'cocubes'):
            user = self._user(f'{name}_full')
            data = self._submit(name, 1.0, user)
            self.assertEqual(data['score'], data['total'])
            self.assertEqual(data['percentage'], 100)
            self.assertTrue(data['saved'])
            cert = data['certificate']
            self.assertEqual(cert['state'], 'certified')
            download = self.client.get(cert['certificate']['download_url'])
            self.assertEqual(download.status_code, 200)
            self.assertTrue(b''.join(download.streaming_content).startswith(b'%PDF'))

    def test_full_score_without_profile_name_asks_for_name(self):
        data = self._submit('amcat', 1.0, self._user('noname', full_name=False))
        self.assertEqual(data['certificate']['state'], 'eligible')
        self.assertTrue(data['certificate']['needs_name'])
        self.assertIsNone(data['certificate']['certificate'])

    def test_partial_and_zero_scores(self):
        for fraction, expected_state in ((0.5, 'locked'), (0.0, 'locked')):
            data = self._submit('cocubes', fraction, self._user(f'u{int(fraction * 100)}'))
            self.assertEqual(data['certificate']['state'], expected_state)
            self.assertEqual(data['percentage'], data['score'] * 100 // data['total'])

    def test_anonymous_user_still_gets_a_score(self):
        data = self._submit('amcat', 1.0)
        self.assertEqual(data['percentage'], 100)
        self.assertFalse(data['authenticated'])
        self.assertIsNone(data['certificate'])

    def test_save_failure_never_breaks_grading(self):
        user = self._user('dbfail')
        with mock.patch('skillup_assessment.models.QuizAttempt.objects.create',
                        side_effect=Exception('table missing')):
            data = self._submit('amcat', 1.0, user)
        self.assertEqual(data['percentage'], 100)
        self.assertFalse(data['saved'])

    def test_bad_payload_is_a_clean_400(self):
        resp = self.client.post(reverse('amcat_submit'), data=json.dumps({'answers': [1, 2]}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())
