"""Tests for JAM session scoring.

Run with:  python manage.py test jam_app
"""
from django.contrib.auth.models import User
from django.test import TestCase

from .models import JAMSession, Topic
from .views import _rule_based_feedback

SPOKEN = (
    "My favourite hobby is reading books because it helps me relax after a long "
    "day at work. I usually read fiction novels in the evening and I try to "
    "finish one book every month. Reading has improved my vocabulary and also "
    "my concentration over the years. I would recommend everyone to build this "
    "habit early because it changes the way you think about problems."
)


class JAMScoringTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('speaker', password='x')
        self.topic = Topic.objects.create(title='My Favourite Hobby')

    def _score(self, transcript, duration):
        session = JAMSession.objects.create(
            user=self.user, topic=self.topic, transcript=transcript, duration=duration
        )
        _rule_based_feedback(session, 1, self.topic.title, 'Easy')
        session.refresh_from_db()
        return session

    def _total(self, session):
        return (session.confidence_score + session.fluency_score
                + session.language_score + session.pronunciation_score
                + session.time_management_score)

    def test_silence_scores_the_minimum(self):
        """Regression: a silent 60s session scored a flat 13/25, including 5/5
        for time management and 3/5 for pronunciation on an empty recording."""
        session = self._score('', 60)

        self.assertEqual(self._total(session), 0)
        for field in ('confidence_score', 'fluency_score', 'language_score',
                      'pronunciation_score', 'time_management_score'):
            self.assertEqual(getattr(session, field), 0, field)

    def test_silence_never_scores_13(self):
        """The old bug produced exactly 13 for any silent session over 5s."""
        for duration in (10, 30, 45, 60, 90):
            self.assertNotEqual(self._total(self._score('', duration)), 13)

    def test_a_real_answer_scores_well(self):
        session = self._score(SPOKEN, 60)

        self.assertGreater(self._total(session), 15)
        self.assertGreaterEqual(session.language_score, 3)

    def test_score_rises_with_the_quality_of_the_answer(self):
        weak = self._total(self._score('I like reading', 20))
        strong = self._total(self._score(SPOKEN, 60))

        self.assertLess(weak, strong)

    def test_every_score_stays_within_range(self):
        for transcript, duration in (('', 0), ('', 60), ('a few words here', 15),
                                     (SPOKEN, 60), (SPOKEN * 3, 60)):
            session = self._score(transcript, duration)
            for field in ('confidence_score', 'fluency_score', 'language_score',
                          'pronunciation_score', 'time_management_score'):
                value = getattr(session, field)
                self.assertGreaterEqual(value, 0, f'{field} for {duration}s')
                self.assertLessEqual(value, 5, f'{field} for {duration}s')
