"""Spoken interview answers: the recording travels with the answer and is
transcribed after the deadline check, and the scored (interpreted) text is
what gets stored and shown."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from career_app.models import (
    JobDescription, Resume, ResumeAnswer, ResumeInterviewSession, ResumeQuestion,
)

User = get_user_model()


class SpokenAnswerSubmitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('spk', 'spk@x.com', 'pw12345!')
        resume = Resume.objects.create(user=self.user, extracted_text='Python developer, 2 years experience.')
        jd = JobDescription.objects.create(user=self.user, text='General Resume Analysis')
        self.session = ResumeInterviewSession.objects.create(
            resume=resume, job_description=jd, camera_verified_at=timezone.now())
        self.client.force_login(self.user)

    def _question(self, seconds_ago):
        return ResumeQuestion.objects.create(
            session=self.session, question_text='What is a Python list?', topic='python',
            presented_at=timezone.now() - timedelta(seconds=seconds_ago))

    def _submit(self, q, live_text, audio=True):
        data = {'question_id': q.id, 'answer_text': live_text, 'spoken': '1'}
        if audio:
            data['audio'] = SimpleUploadedFile('recording.webm', b'fake-audio', content_type='audio/webm')
        return self.client.post(reverse('resume_submit_answer'), data)

    @mock.patch('career_app.views.evaluate_answer')
    @mock.patch('career_app.views._transcribe_interview_audio')
    def test_server_transcript_is_scored_and_interpreted_text_shown(self, stt, evaluate):
        stt.return_value = 'list is mutable we can change it'
        evaluate.return_value = {'score': 5, 'feedback': 'ok', 'interpreted': 'A list is mutable.'}
        q = self._question(10)
        resp = self._submit(q, 'list is mutable we can change')
        self.assertEqual(evaluate.call_args[0][1], 'list is mutable we can change it')
        self.assertTrue(evaluate.call_args.kwargs['spoken'])
        self.assertEqual(resp.json()['display_text'], 'A list is mutable.')
        self.assertEqual(ResumeAnswer.objects.get(question=q).text, 'A list is mutable.')

    @mock.patch('career_app.views.evaluate_answer')
    @mock.patch('career_app.views._transcribe_interview_audio', return_value='')
    def test_live_captions_used_when_transcription_fails(self, stt, evaluate):
        evaluate.return_value = {'score': 4, 'feedback': 'ok'}
        q = self._question(10)
        resp = self._submit(q, 'list is mutable')
        self.assertEqual(evaluate.call_args[0][1], 'list is mutable')
        self.assertEqual(resp.json()['score'], 4)

    @mock.patch('career_app.views.evaluate_answer')
    @mock.patch('career_app.views._transcribe_interview_audio')
    def test_audio_only_answer_is_not_scored_as_empty(self, stt, evaluate):
        """No live captions yet, but the recording has the answer."""
        stt.return_value = 'a list is an ordered mutable collection'
        evaluate.return_value = {'score': 5, 'feedback': 'ok'}
        q = self._question(31)   # auto-submitted just after the 30s timer
        resp = self._submit(q, '')
        self.assertEqual(resp.json()['score'], 5)
        self.assertTrue(resp.json()['timed_out'])

    @mock.patch('career_app.views.evaluate_answer')
    @mock.patch('career_app.views._transcribe_interview_audio')
    def test_late_answer_is_discarded_without_calling_the_speech_service(self, stt, evaluate):
        q = self._question(60)
        resp = self._submit(q, 'anything')
        stt.assert_not_called()
        evaluate.assert_not_called()
        self.assertEqual(resp.json()['score'], 0)

    @mock.patch('career_app.views.evaluate_answer')
    @mock.patch('career_app.views._transcribe_interview_audio', return_value='')
    def test_resent_answer_returns_stored_result(self, stt, evaluate):
        """The browser re-sends if the response was lost; even after the timer
        it must get the original score back, not a late-answer zero."""
        from core.models import ScoreRecord
        evaluate.return_value = {'score': 4, 'feedback': 'Good.'}
        q = self._question(10)
        self._submit(q, 'a list is mutable')
        ResumeQuestion.objects.filter(id=q.id).update(presented_at=timezone.now() - timedelta(seconds=90))
        resp = self._submit(q, 'a list is mutable')
        self.assertEqual(resp.json()['score'], 4)
        self.assertEqual(evaluate.call_count, 1)
        self.assertEqual(ScoreRecord.objects.filter(user=self.user, module='interview').count(), 1)
