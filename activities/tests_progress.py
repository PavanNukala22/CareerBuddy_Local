"""Performance-based progress (activities/progress.py) and server-side
grading (activities/grading.py).

Run:  python manage.py test activities.tests_progress
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .grading import grade_submission
from .models import Activity, SubActivity, Exercise, Question, BingoCard, UserExerciseResult
from . import progress as perf


def make_activity(order=1, title='Grammar Basics', category='vocabulary'):
    return Activity.objects.create(
        order=order, title=title, category=category, level='B1',
        duration='30 min', materials='-', objective='-',
    )


def make_exercise(sub, order=1, kind='mcq', n_questions=10, correct='a'):
    ex = Exercise.objects.create(sub_activity=sub, title=f'Ex{order}', exercise_type=kind,
                                 instructions='-', order=order)
    for i in range(1, n_questions + 1):
        Question.objects.create(exercise=ex, order=i, question_text=f'Q{i}',
                                option_a='A', option_b='B', correct_answer=correct)
    return ex


def result(user, ex, score, max_score):
    return UserExerciseResult.objects.create(user=user, exercise=ex, score=score, max_score=max_score)


class ProgressCalculationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('learner', password='x')
        cls.act = make_activity()
        cls.sub1 = SubActivity.objects.create(activity=cls.act, order=1, title='S1', description='-', instructions='-')
        cls.sub2 = SubActivity.objects.create(activity=cls.act, order=2, title='S2', description='-', instructions='-')
        cls.ex1 = make_exercise(cls.sub1, 1)
        cls.ex2 = make_exercise(cls.sub1, 2)
        cls.ex3 = make_exercise(cls.sub2, 1)

    def test_seven_of_ten_is_seventy_percent(self):
        result(self.user, self.ex1, 7, 10)
        self.assertEqual(perf.exercise_percentages(self.user)[self.ex1.id], 70.0)
        p = perf.summarize([self.ex1.id], perf.exercise_percentages(self.user))
        self.assertEqual(p.percent, 70)

    def test_unattempted_exercises_count_as_zero(self):
        result(self.user, self.ex1, 10, 10)
        p = perf.progress_for_activity(self.user, self.act)
        self.assertEqual(p.percent, 33)          # (100 + 0 + 0) / 3
        self.assertEqual((p.attempted, p.total, p.status), (1, 3, 'in_progress'))

    def test_attempting_everything_badly_is_completed_but_low(self):
        for ex in (self.ex1, self.ex2, self.ex3):
            result(self.user, ex, 2, 10)
        p = perf.progress_for_activity(self.user, self.act)
        self.assertEqual((p.percent, p.status, p.band), (20, 'completed', 'danger'))

    def test_starting_without_a_result_is_zero(self):
        p = perf.progress_for_activity(self.user, self.act)
        self.assertEqual((p.percent, p.status), (0, 'not_started'))

    def test_sub_activity_progress(self):
        result(self.user, self.ex1, 8, 10)
        result(self.user, self.ex2, 6, 10)
        p = perf.progress_for_sub_activity(self.user, self.sub1)
        self.assertEqual((p.percent, p.status), (70, 'completed'))

    def test_latest_attempt_counts_by_default(self):
        result(self.user, self.ex1, 9, 10)
        result(self.user, self.ex1, 4, 10)       # newer, weaker attempt
        self.assertEqual(perf.exercise_percentages(self.user)[self.ex1.id], 40.0)

    @override_settings(ACTIVITY_PROGRESS_SCORING='best')
    def test_best_attempt_policy(self):
        result(self.user, self.ex1, 9, 10)
        result(self.user, self.ex1, 4, 10)
        self.assertEqual(perf.exercise_percentages(self.user)[self.ex1.id], 90.0)

    def test_different_max_scores_are_normalised(self):
        # AI modules score out of 25, writing out of 100, MCQ out of N.
        result(self.user, self.ex1, 20, 25)      # 80%
        result(self.user, self.ex2, 60, 100)     # 60%
        result(self.user, self.ex3, 7, 10)       # 70%
        self.assertEqual(perf.progress_for_activity(self.user, self.act).percent, 70)

    def test_get_completion_rate_is_performance(self):
        result(self.user, self.ex1, 7, 10)
        result(self.user, self.ex2, 7, 10)
        result(self.user, self.ex3, 7, 10)
        self.assertEqual(self.act.get_completion_rate(self.user), 70)

    def test_bands(self):
        self.assertEqual(perf.Progress(percent=85, attempted=1, total=1).band, 'success')
        self.assertEqual(perf.Progress(percent=50, attempted=1, total=1).band, 'warning')
        self.assertEqual(perf.Progress(percent=49, attempted=1, total=1).band, 'danger')
        self.assertEqual(perf.Progress(percent=0, attempted=0, total=1).band, 'secondary')

    def test_workshop_progress_from_sessions(self):
        from core.models import ScoreRecord
        gd = make_activity(order=99, title='Group Discussion', category='workshop')
        ScoreRecord.objects.create(user=self.user, module='gd', score=10, max_score=25)
        ScoreRecord.objects.create(user=self.user, module='gd', score=20, max_score=25)
        p = perf.activity_progress(gd, {}, perf.workshop_progress(self.user))
        self.assertEqual((p.percent, p.attempted, p.status), (80, 2, 'in_progress'))


class GradingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        act = make_activity()
        cls.sub = SubActivity.objects.create(activity=act, order=1, title='S', description='-', instructions='-')

    def test_mcq_is_regraded_on_the_server(self):
        ex = make_exercise(self.sub, 1, 'mcq', 10, correct='b')
        answers = {str(i): {'chosen': 'b' if i <= 7 else 'a'} for i in range(1, 11)}
        # The browser claims 10/10; the answers say 7/10.
        self.assertEqual(grade_submission(ex, 10, 10, answers), (7, 10))

    def test_fill_blank_is_case_insensitive(self):
        ex = make_exercise(self.sub, 2, 'fill_blank', 3, correct='Deadline')
        answers = {'1': {'given': ' deadline '}, '2': {'given': 'DEADLINE'}, '3': {'given': 'date'}}
        self.assertEqual(grade_submission(ex, 3, 3, answers), (2, 3))

    def test_matching_uses_pairs(self):
        ex = make_exercise(self.sub, 3, 'matching', 4)
        answers = {'1': {'paired': '1'}, '2': {'paired': '3'}, '3': {'paired': '2'}, '4': {'paired': '4'}}
        self.assertEqual(grade_submission(ex, 4, 4, answers), (2, 4))

    def test_bingo_counts_only_real_matches(self):
        ex = make_exercise(self.sub, 4, 'bingo', 0)
        for w in ('agenda', 'minutes', 'quorum'):
            BingoCard.objects.create(exercise=ex, word=w, definition='-')
        answers = {'w1': {'chosen': 'agenda', 'target': 'agenda'},
                   'w2': {'chosen': 'fake', 'target': 'fake'},
                   'w3': {'chosen': 'quorum', 'target': 'minutes'}}
        self.assertEqual(grade_submission(ex, 3, 3, answers), (1, 3))

    def test_writing_score_is_clamped(self):
        ex = make_exercise(self.sub, 5, 'writing', 1)
        self.assertEqual(grade_submission(ex, 250, 999, {}), (100, 100))
        self.assertEqual(grade_submission(ex, -5, 100, {}), (0, 100))

    def test_timer_max_is_task_count(self):
        ex = make_exercise(self.sub, 6, 'timer', 3)
        self.assertEqual(grade_submission(ex, 9, 9, {}), (3, 3))


class SubmitEndpointTests(TestCase):
    """End-to-end through submit_exercise (needs the full project URLconf)."""

    @classmethod
    def setUpTestData(cls):
        from django.utils import timezone
        cls.user = User.objects.create_user('pro_learner', password='pass12345')
        profile = cls.user.profile
        profile.plan_type = 'pro'
        profile.is_pro = True
        profile.subscription_start = timezone.now()
        profile.save()
        act = make_activity(order=50, title='Meeting Vocabulary')
        sub = SubActivity.objects.create(activity=act, order=1, title='S', description='-', instructions='-')
        cls.ex = make_exercise(sub, 1, 'mcq', 10, correct='c')
        cls.ex2 = make_exercise(sub, 2, 'mcq', 10, correct='c')

    def test_submit_stores_verified_score_and_returns_progress(self):
        self.client.force_login(self.user)
        answers = {str(i): {'chosen': 'c' if i <= 7 else 'a'} for i in range(1, 11)}
        resp = self.client.post(
            reverse('submit_exercise', args=[self.ex.pk]),
            data=json.dumps({'score': 10, 'max_score': 10, 'answers': answers}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual((data['score'], data['max_score'], data['percentage']), (7, 10, 70))
        self.assertEqual(data['sub_progress']['percent'], 35)        # (70 + 0) / 2
        self.assertEqual(data['activity_progress']['attempted'], 1)
        stored = UserExerciseResult.objects.get(user=self.user, exercise=self.ex)
        self.assertEqual((stored.score, stored.max_score), (7, 10))
