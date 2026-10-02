"""§12.5 AI Skill Modules (FR-AIM) — tests.

External AI (Sarvam / LanguageTool) is always mocked or disabled here; no test in
this module may make a network call.
"""

import json
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .agents.base import BaseAgent
from .models import (
    Activity, SubActivity, Exercise,
    UserProgress, UserExerciseResult,
)


class AIMTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        # A Free Plan activity (FR-LMS-02) — its title must be one of
        # FREE_PLAN_ACTIVITY_TITLES in activities/views.py.
        cls.speaking = Activity.objects.create(
            order=24, title="Listen & Learn", category="speaking",
            level="Intermediate", duration="30 min", materials="-", objective="-",
        )
        cls.speaking_sub = SubActivity.objects.create(
            activity=cls.speaking, order=1, title="SpeakSub", description="-", instructions="-")
        cls.speaking_ex = Exercise.objects.create(
            sub_activity=cls.speaking_sub, title="SpeakEx", exercise_type="writing",
            instructions="-", order=1)

        # A paid-plan activity, used for authorization tests.
        cls.writing_act = Activity.objects.create(
            order=7, title="Professional Passage Writing", category="writing",
            level="Intermediate", duration="30 min", materials="-", objective="-",
        )
        cls.writing_sub = SubActivity.objects.create(
            activity=cls.writing_act, order=1, title="WriteSub", description="-", instructions="-")
        cls.writing_ex = Exercise.objects.create(
            sub_activity=cls.writing_sub, title="WriteEx", exercise_type="writing",
            instructions="-", order=1)

    @classmethod
    def make_user(cls, username, plan_type='pro', is_pro=True):
        from django.utils import timezone
        user = User.objects.create_user(username=username, password='pass12345')
        profile = user.profile
        profile.plan_type = plan_type
        profile.is_pro = is_pro
        # A paid plan without a subscription window counts as expired and reverts
        # to Free on resolution, so give paid fixtures a live start date.
        if plan_type != 'free':
            profile.subscription_start = timezone.now()
        profile.save()
        return user


def ok_result(scores):
    """A successful safe_run envelope carrying the given scores."""
    return {
        'success': True,
        'data': {'scores': scores, 'text': 'hello world', 'issues': [], 'improved_passage': ''},
        'error': None,
        'meta': {'module': 'test', 'duration': 0.1, 'attempt': 1},
    }


# --------------------------------------------------------------------------- #
#  FR-AIM-07 — Retry and safe execution
# --------------------------------------------------------------------------- #

@mock.patch('activities.agents.base.time.sleep', lambda *a, **k: None)
class SafeExecutionTests(TestCase):
    """FR-AIM-07: retries up to three times, always a structured envelope."""

    def _agent(self, side_effect):
        agent = BaseAgent('unit')
        agent.run = mock.Mock(side_effect=side_effect)
        return agent

    def test_success_first_attempt(self):
        agent = self._agent([{'scores': {'overall': 80}}])
        result = agent.safe_run({})
        self.assertTrue(result['success'])
        self.assertEqual(result['meta']['attempt'], 1)
        self.assertIsNone(result['error'])
        self.assertEqual(agent.run.call_count, 1)

    def test_one_failure_then_success(self):
        agent = self._agent([RuntimeError('boom'), {'scores': {}}])
        result = agent.safe_run({})
        self.assertTrue(result['success'])
        self.assertEqual(result['meta']['attempt'], 2)
        self.assertEqual(agent.run.call_count, 2)

    def test_two_failures_then_success(self):
        agent = self._agent([RuntimeError('a'), RuntimeError('b'), {'scores': {}}])
        result = agent.safe_run({})
        self.assertTrue(result['success'])
        self.assertEqual(result['meta']['attempt'], 3)
        self.assertEqual(agent.run.call_count, 3)

    def test_all_attempts_fail_returns_structured_error(self):
        agent = self._agent([RuntimeError('x')] * 5)
        result = agent.safe_run({})
        self.assertFalse(result['success'])
        self.assertEqual(result['data'], {})
        self.assertIsInstance(result['error'], str)
        self.assertEqual(result['meta']['attempt'], 3)

    def test_never_retries_more_than_three_times(self):
        agent = self._agent([RuntimeError('x')] * 10)
        agent.safe_run({})
        self.assertEqual(agent.run.call_count, 3)

    def test_permanent_exception_does_not_propagate(self):
        agent = self._agent(KeyError('missing'))
        try:
            result = agent.safe_run({})
        except Exception as exc:  # pragma: no cover - the assertion below reports it
            self.fail(f'safe_run raised instead of returning an envelope: {exc!r}')
        self.assertFalse(result['success'])

    def test_envelope_always_has_required_keys(self):
        for side_effect in ([{'ok': 1}], [RuntimeError('x')] * 3):
            agent = self._agent(side_effect)
            result = agent.safe_run({})
            self.assertEqual(set(result), {'success', 'data', 'error', 'meta'})
            self.assertEqual(set(result['meta']), {'module', 'duration', 'attempt'})

    def test_input_error_is_not_retried(self):
        """A submission the learner must fix cannot be improved by retrying."""
        from .agents.base import AgentInputError
        agent = self._agent(AgentInputError('Please write at least 500 characters.'))
        result = agent.safe_run({})
        self.assertFalse(result['success'])
        self.assertEqual(agent.run.call_count, 1)
        self.assertEqual(result['meta']['attempt'], 1)

    def test_input_error_message_reaches_user_verbatim(self):
        """No "Internal agent error:" prefix on guidance written for the learner."""
        from .agents.base import AgentInputError
        agent = self._agent(AgentInputError('Please write something before analyzing.'))
        result = agent.safe_run({})
        self.assertEqual(result['error'], 'Please write something before analyzing.')
        self.assertNotIn('Internal agent error', result['error'])

    def test_infrastructure_errors_still_retry_and_are_labelled(self):
        agent = self._agent([RuntimeError('connection reset')] * 3)
        result = agent.safe_run({})
        self.assertEqual(agent.run.call_count, 3)
        self.assertIn('Internal agent error', result['error'])

    def test_base_run_is_abstract(self):
        with self.assertRaises(NotImplementedError):
            BaseAgent('unit').run({})

    def test_api_view_wrapper_is_importable_and_functional(self):
        """UNUSED_BROKEN_CODE guard: the helper referenced json without importing it."""
        from django.http import JsonResponse as JR
        from .agents.base import api_view_wrapper

        @api_view_wrapper
        def view(request):
            return JR({'value': 1})

        resp = view(None)
        body = json.loads(resp.content)
        self.assertEqual(set(body), {'success', 'data', 'error'})
        self.assertTrue(body['success'])


# --------------------------------------------------------------------------- #
#  FR-AIM-05 — Score normalisation and persistence
# --------------------------------------------------------------------------- #

@override_settings(SARVAM_API_KEY='')
class ProviderScoreScaleTests(TestCase):
    """FR-AIM-05: provider scores must reach normalisation on a 0-100 scale."""

    def test_fractions_are_scaled_to_percent(self):
        from .agents.utils import normalise_score_scale
        self.assertEqual(
            normalise_score_scale({'accuracy': 0.8, 'grammar': 0.6, 'pronunciation': 1.0}),
            {'accuracy': 80, 'grammar': 60, 'pronunciation': 100})

    def test_percent_values_pass_through(self):
        from .agents.utils import normalise_score_scale
        self.assertEqual(
            normalise_score_scale({'accuracy': 85.0, 'overall': 31, 'fluency': 76}),
            {'accuracy': 85, 'overall': 31, 'fluency': 76})

    def test_out_of_range_is_clamped(self):
        from .agents.utils import normalise_score_scale
        self.assertEqual(normalise_score_scale({'a': 120, 'b': -5}), {'a': 100, 'b': 0})

    def test_non_numeric_values_dropped(self):
        from .agents.utils import normalise_score_scale
        self.assertEqual(
            normalise_score_scale({'a': 'high', 'b': None, 'c': True, 'd': 70}), {'d': 70})

    def test_non_dict_returns_empty(self):
        from .agents.utils import normalise_score_scale
        self.assertEqual(normalise_score_scale(None), {})
        self.assertEqual(normalise_score_scale([1, 2]), {})

    def test_fractional_score_would_otherwise_persist_as_zero(self):
        """Regression: accuracy 0.8 scored 0/25 before scaling was applied."""
        from .agents.utils import normalise_score_scale
        from .views import _normalised_module_score
        raw = {'accuracy': 0.8}
        self.assertEqual(_normalised_module_score(raw, 'accuracy'), 0)
        self.assertEqual(
            _normalised_module_score(normalise_score_scale(raw), 'accuracy'), 20)

    def test_scale_directive_present_in_prompts(self):
        from .agents import utils
        self.assertIn('0 to 100', utils.SCORE_SCALE_DIRECTIVE)


class ScoreNormalisationTests(AIMTestDataMixin, TestCase):
    """FR-AIM-05: round(raw x 25 / 100), clamped 0-25, max_score 25, attempt++."""

    def _post_speaking(self, user, scores):
        self.client.force_login(user)
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run',
                        return_value=ok_result(scores)):
            return self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hello world', 'duration_seconds': '5', 'pause_count': '1'},
            )

    def test_normalisation_formula_and_bounds(self):
        # FR-AIM-05 specifies round(raw x 25 / 100) literally. Python's round()
        # is banker's rounding, so raw=50 -> round(12.5) -> 12, not 13. The
        # expectations below follow the FSD formula as written.
        cases = [
            (0, 0), (50, 12), (100, 25), (70, 18), (99, 25), (1, 0),
            (200, 25),     # above range -> clamped
            (-50, 0),      # below range -> clamped
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                user = self.make_user(f'norm{raw}')
                self._post_speaking(user, {'overall': raw})
                result = UserExerciseResult.objects.get(user=user, exercise=self.speaking_ex)
                self.assertEqual(result.score, expected)
                self.assertEqual(result.max_score, 25)

    def test_falls_back_to_fluency_when_overall_absent(self):
        user = self.make_user('fluencyfallback')
        self._post_speaking(user, {'fluency': 80})
        result = UserExerciseResult.objects.get(user=user, exercise=self.speaking_ex)
        self.assertEqual(result.score, 20)

    def test_attempt_number_increments_across_analyses(self):
        user = self.make_user('attempts')
        for expected in (1, 2, 3):
            self._post_speaking(user, {'overall': 60})
            latest = UserExerciseResult.objects.filter(
                user=user, exercise=self.speaking_ex).order_by('-attempt_number').first()
            self.assertEqual(latest.attempt_number, expected)
        self.assertEqual(
            UserExerciseResult.objects.filter(user=user, exercise=self.speaking_ex).count(), 3)

    def test_sub_activity_marked_complete(self):
        user = self.make_user('completion')
        self._post_speaking(user, {'overall': 60})
        progress = UserProgress.objects.get(user=user, sub_activity=self.speaking_sub)
        self.assertEqual(progress.status, 'completed')

    def test_non_numeric_ai_score_does_not_crash(self):
        """A malformed AI payload must not produce a 500 (BR-25 / FR-AIM-07)."""
        user = self.make_user('malformedscore')
        resp = self._post_speaking(user, {'overall': 'not-a-number'})
        self.assertLess(resp.status_code, 500)

    def test_failed_analysis_persists_nothing(self):
        user = self.make_user('failnosave')
        self.client.force_login(user)
        envelope = {'success': False, 'data': {}, 'error': 'nope',
                    'meta': {'module': 'speaking', 'duration': 0.1, 'attempt': 3}}
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run', return_value=envelope):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': '', 'duration_seconds': '0', 'pause_count': '0'},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(UserExerciseResult.objects.filter(user=user).exists())


# --------------------------------------------------------------------------- #
#  FR-AIM-01 — Speaking analysis
# --------------------------------------------------------------------------- #

@override_settings(SARVAM_API_KEY='')
class SpeakingAnalysisTests(AIMTestDataMixin, TestCase):

    def test_requires_authentication(self):
        resp = self.client.post(reverse('analyze_speaking', args=[self.speaking_ex.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/users/login', resp.url)

    def test_get_not_allowed(self):
        self.client.force_login(self.make_user('spget'))
        resp = self.client.get(reverse('analyze_speaking', args=[self.speaking_ex.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_invalid_exercise_id_404(self):
        self.client.force_login(self.make_user('sp404'))
        resp = self.client.post(reverse('analyze_speaking', args=[999999]))
        self.assertEqual(resp.status_code, 404)

    def test_valid_submission_returns_scores_and_transcript(self):
        user = self.make_user('spvalid')
        self.client.force_login(user)
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run',
                        return_value=ok_result({'overall': 80, 'fluency': 75})):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hello world', 'duration_seconds': '12.5', 'pause_count': '2'},
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body['success'])
        self.assertIn('transcript', body['data'])
        self.assertEqual(body['data']['scores']['overall'], 80)

    def test_audio_upload_accepted(self):
        user = self.make_user('spaudio')
        self.client.force_login(user)
        audio = SimpleUploadedFile('a.webm', b'\x00' * 64, content_type='audio/webm')
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run',
                        return_value=ok_result({'overall': 60})):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'audio': audio, 'client_transcript': 'hi', 'duration_seconds': '3', 'pause_count': '0'},
            )
        self.assertEqual(resp.status_code, 200)

    def test_malformed_duration_does_not_500(self):
        user = self.make_user('spbadduration')
        self.client.force_login(user)
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run',
                        return_value=ok_result({'overall': 60})):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hi', 'duration_seconds': '', 'pause_count': ''},
            )
        self.assertLess(resp.status_code, 500)

    def test_non_numeric_duration_does_not_500(self):
        user = self.make_user('spbadduration2')
        self.client.force_login(user)
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run',
                        return_value=ok_result({'overall': 60})):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hi', 'duration_seconds': 'abc', 'pause_count': 'xyz'},
            )
        self.assertLess(resp.status_code, 500)

    def test_agent_failure_returns_structured_error_not_500(self):
        user = self.make_user('spfail')
        self.client.force_login(user)
        envelope = {'success': False, 'data': {}, 'error': 'Internal agent error: no speech',
                    'meta': {'module': 'speaking', 'duration': 0.1, 'attempt': 3}}
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run', return_value=envelope):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': '', 'duration_seconds': '0', 'pause_count': '0'},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['success'])

    def test_user_isolation(self):
        user_a = self.make_user('spa')
        user_b = self.make_user('spb')
        self.client.force_login(user_a)
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run',
                        return_value=ok_result({'overall': 80})):
            self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hi', 'duration_seconds': '5', 'pause_count': '0'},
            )
        self.assertTrue(UserExerciseResult.objects.filter(user=user_a).exists())
        self.assertFalse(UserExerciseResult.objects.filter(user=user_b).exists())

    def test_completes_without_sarvam_key(self):
        """TS-30 / BR-25: with the Sarvam key removed the feature still completes."""
        user = self.make_user('spnokey')
        self.client.force_login(user)
        with mock.patch('activities.agents.utils.transcribe_with_sarvam') as stt, \
             mock.patch('activities.agents.utils.analyze_text_with_sarvam_chat') as chat:
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hello there friend', 'duration_seconds': '5', 'pause_count': '0'},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])
        stt.assert_not_called()
        chat.assert_not_called()

    def test_completes_when_languagetool_unreachable(self):
        """BR-25: the offline grammar provider failing must not fail the request."""
        user = self.make_user('spnolt')
        self.client.force_login(user)
        with mock.patch('activities.agents.utils.requests.post',
                        side_effect=OSError('network down')):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hello there friend', 'duration_seconds': '5', 'pause_count': '0'},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])


# --------------------------------------------------------------------------- #
#  FR-AIM-02 — Writing analysis
# --------------------------------------------------------------------------- #

@override_settings(SARVAM_API_KEY='')
class WritingAnalysisTests(AIMTestDataMixin, TestCase):

    def test_requires_authentication(self):
        resp = self.client.post(reverse('analyze_writing', args=[self.speaking_ex.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_get_not_allowed(self):
        self.client.force_login(self.make_user('wrget'))
        resp = self.client.get(reverse('analyze_writing', args=[self.speaking_ex.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_formdata_path(self):
        user = self.make_user('wrform')
        self.client.force_login(user)
        with mock.patch('activities.agents.writing.WritingAgent.safe_run',
                        return_value=ok_result({'overall': 88})) as run:
            resp = self.client.post(
                reverse('analyze_writing', args=[self.speaking_ex.pk]),
                {'text': 'x' * 600, 'language': 'english'},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(run.call_args[0][0]['text'], 'x' * 600)

    def test_json_body_path(self):
        user = self.make_user('wrjson')
        self.client.force_login(user)
        with mock.patch('activities.agents.writing.WritingAgent.safe_run',
                        return_value=ok_result({'overall': 88})) as run:
            resp = self.client.post(
                reverse('analyze_writing', args=[self.speaking_ex.pk]),
                data=json.dumps({'text': 'y' * 600, 'language': 'english'}),
                content_type='application/json',
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(run.call_args[0][0]['text'], 'y' * 600)

    def test_malformed_json_does_not_500(self):
        user = self.make_user('wrbadjson')
        self.client.force_login(user)
        with mock.patch('activities.agents.writing.WritingAgent.safe_run',
                        return_value=ok_result({'overall': 50})):
            resp = self.client.post(
                reverse('analyze_writing', args=[self.speaking_ex.pk]),
                data='{broken json', content_type='application/json',
            )
        self.assertLess(resp.status_code, 500)

    def test_empty_text_returns_structured_failure(self):
        user = self.make_user('wrempty')
        self.client.force_login(user)
        resp = self.client.post(
            reverse('analyze_writing', args=[self.speaking_ex.pk]), {'text': ''})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body['success'])
        self.assertFalse(UserExerciseResult.objects.filter(user=user).exists())

    def test_validation_messages_are_learner_facing(self):
        """writing.js renders result.error directly, so it must read as guidance."""
        user = self.make_user('wrmsg')
        self.client.force_login(user)
        for text in ['', 'too short', 'x' * 1200]:
            with self.subTest(text=text[:12]):
                resp = self.client.post(
                    reverse('analyze_writing', args=[self.speaking_ex.pk]), {'text': text})
                error = resp.json()['error']
                self.assertNotIn('Internal agent error', error)
                self.assertTrue(error.startswith('Please'), error)

    def test_short_text_rejected_by_agent(self):
        user = self.make_user('wrshort')
        self.client.force_login(user)
        resp = self.client.post(
            reverse('analyze_writing', args=[self.speaking_ex.pk]), {'text': 'too short'})
        self.assertFalse(resp.json()['success'])

    def test_result_persisted_with_corrected_version_and_issues(self):
        user = self.make_user('wrpersist')
        self.client.force_login(user)
        payload = ok_result({'overall': 88})
        payload['data']['improved_passage'] = 'corrected text'
        payload['data']['issues'] = [{'phrase': 'teh', 'suggestion': 'the'}]
        with mock.patch('activities.agents.writing.WritingAgent.safe_run', return_value=payload):
            resp = self.client.post(
                reverse('analyze_writing', args=[self.speaking_ex.pk]), {'text': 'z' * 600})
        body = resp.json()
        self.assertEqual(body['data']['improved_passage'], 'corrected text')
        self.assertEqual(len(body['data']['issues']), 1)
        result = UserExerciseResult.objects.get(user=user, exercise=self.speaking_ex)
        self.assertEqual(result.score, 22)
        self.assertEqual(result.max_score, 25)

    def test_offline_fallback_without_api_key(self):
        """BR-25 / TS-30: usable result with no AI provider."""
        user = self.make_user('wroffline')
        self.client.force_login(user)
        with mock.patch('activities.agents.utils.analyze_text_with_sarvam_chat') as chat:
            resp = self.client.post(
                reverse('analyze_writing', args=[self.speaking_ex.pk]),
                {'text': 'This is a sentence about business communication. ' * 15},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])
        chat.assert_not_called()


# --------------------------------------------------------------------------- #
#  Authorization / plan gating on AI endpoints (Category C)
# --------------------------------------------------------------------------- #

@override_settings(SARVAM_API_KEY='')
class AIEndpointAuthorizationTests(AIMTestDataMixin, TestCase):
    """A Free Plan user must not be able to consume paid AI analysis."""

    ENDPOINTS = ['analyze_speaking', 'analyze_writing', 'analyze_listening', 'analyze_reading']

    def test_free_user_blocked_on_paid_activity_exercise(self):
        user = self.make_user('freeai', plan_type='free', is_pro=False)
        self.client.force_login(user)
        for name in self.ENDPOINTS:
            with self.subTest(endpoint=name):
                resp = self.client.post(
                    reverse(name, args=[self.writing_ex.pk]),
                    {'text': 'q' * 600, 'client_transcript': 'hi',
                     'duration_seconds': '5', 'pause_count': '0'},
                )
                self.assertEqual(resp.status_code, 403)
        self.assertFalse(UserExerciseResult.objects.filter(user=user).exists())

    def test_free_user_allowed_on_free_plan_activity(self):
        user = self.make_user('freeaiok', plan_type='free', is_pro=False)
        self.client.force_login(user)
        with mock.patch('activities.agents.speaking.SpeakingAgent.safe_run',
                        return_value=ok_result({'overall': 60})):
            resp = self.client.post(
                reverse('analyze_speaking', args=[self.speaking_ex.pk]),
                {'client_transcript': 'hi', 'duration_seconds': '5', 'pause_count': '0'},
            )
        self.assertEqual(resp.status_code, 200)

    def test_paid_user_allowed_on_paid_activity(self):
        user = self.make_user('paidai', plan_type='normal', is_pro=False)
        self.client.force_login(user)
        with mock.patch('activities.agents.writing.WritingAgent.safe_run',
                        return_value=ok_result({'overall': 70})):
            resp = self.client.post(
                reverse('analyze_writing', args=[self.writing_ex.pk]), {'text': 'w' * 600})
        self.assertEqual(resp.status_code, 200)

    def test_csrf_enforced_on_ai_endpoints(self):
        user = self.make_user('csrfai')
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.force_login(user)
        resp = csrf_client.post(
            reverse('analyze_writing', args=[self.speaking_ex.pk]), {'text': 'v' * 600})
        self.assertEqual(resp.status_code, 403)
