"""Option rotation + grading for the mock tests.

The question banks are position-biased (oop: answer A in 289/300, tensorflow:
B in 290/300), so options are rotated per question before being served and the
submitted index is mapped back at grading time.

Run:  python manage.py test activities.tests_option_rotation
"""
import collections

from django.test import SimpleTestCase

from activities import views


Q = {"id": 7, "q": "?", "options": ["alpha", "beta", "gamma", "delta"], "answer": 0,
     "explanation": "-"}


class OptionRotationTests(SimpleTestCase):
    def test_served_options_are_a_permutation(self):
        served = views._serve_options(Q, "salt")
        self.assertEqual(sorted(served), sorted(Q["options"]))

    def test_picking_the_correct_text_is_graded_correct(self):
        salt = "salt"
        served = views._serve_options(Q, salt)
        chosen = served.index("alpha")            # what the candidate clicks
        attempted, is_correct, correct_display = views._grade_choice(Q, chosen, salt)
        self.assertTrue(attempted)
        self.assertTrue(is_correct)
        self.assertEqual(correct_display, chosen)

    def test_picking_a_wrong_option_is_graded_wrong(self):
        salt = "salt"
        served = views._serve_options(Q, salt)
        _, is_correct, _ = views._grade_choice(Q, served.index("gamma"), salt)
        self.assertFalse(is_correct)

    def test_unanswered_is_not_attempted(self):
        attempted, is_correct, _ = views._grade_choice(Q, -1, "salt")
        self.assertFalse(attempted)
        self.assertFalse(is_correct)

    def test_a_duplicated_option_still_grades_as_correct(self):
        dup = dict(Q, options=["alpha", "alpha", "gamma", "delta"], answer=0)
        salt = "salt"
        served = views._serve_options(dup, salt)
        for i, text in enumerate(served):
            if text == "alpha":
                _, is_correct, _ = views._grade_choice(dup, i, salt)
                self.assertTrue(is_correct, f"option {i} holds the correct text")

    def test_correct_answer_is_spread_across_all_four_positions(self):
        """The real bug: with a fixed bank the answer sat at one letter."""
        seen = collections.Counter()
        for qid in range(300):
            q = dict(Q, id=qid)
            served = views._serve_options(q, "salt")
            seen[served.index("alpha")] += 1
        self.assertEqual(len(seen), 4)
        for position in range(4):
            self.assertGreater(seen[position], 300 // 10)

    def test_questions_with_duplicate_options_are_dropped_from_the_pool(self):
        pool = [Q, dict(Q, id=8, options=["a", "a", "b", "c"])]
        self.assertEqual([q["id"] for q in views._usable_questions(pool)], [7])

    def test_questions_with_spreadsheet_error_options_are_dropped(self):
        pool = [Q, dict(Q, id=9, options=["#NAME?", "b", "c", "d"]),
                dict(Q, id=10, options=["a", "", "c", "d"])]
        self.assertEqual([q["id"] for q in views._usable_questions(pool)], [7])


class CertificateBookkeepingTests(SimpleTestCase):
    """Every mock-test submit endpoint must run the same after-grading
    bookkeeping — record the attempt AND issue the certificate when earned.
    Only AMCAT and CoCubes did; the 25 subject quizzes saved the attempt and
    stopped there."""

    def test_every_submit_endpoint_calls_after_grading(self):
        import inspect
        for endpoint in (views.quiz_submit, views.oop_quiz_submit,
                         views.amcat_submit, views.cocubes_submit):
            source = inspect.getsource(endpoint)
            self.assertIn('after_grading', source, f'{endpoint.__name__} skips after_grading')

    def test_no_endpoint_writes_quizattempt_directly(self):
        """record_attempt() in skillup_assessment.services is the one writer —
        a direct create bypasses certificate generation."""
        import inspect
        for endpoint in (views.quiz_submit, views.oop_quiz_submit):
            self.assertNotIn('QuizAttempt.objects.create', inspect.getsource(endpoint))


class RotationIsReproducibleTests(SimpleTestCase):
    """Fetch and submit are separate requests: the order must be recomputable,
    never stored. A mismatch would grade every answer against the wrong option."""

    class _Req:
        def __init__(self, user):
            self.user = user

    class _User:
        def __init__(self, pk, authed=True):
            self.pk, self.is_authenticated = pk, authed

    def test_same_user_gets_the_same_order_on_both_requests(self):
        fetch = views._quiz_salt(self._Req(self._User(9)), create=True)
        submit = views._quiz_salt(self._Req(self._User(9)))
        self.assertEqual(fetch, submit)
        self.assertEqual(views._serve_options(Q, fetch), views._serve_options(Q, submit))

    def test_anonymous_user_is_also_stable(self):
        anon = self._User(None, authed=False)
        self.assertEqual(views._quiz_salt(self._Req(anon), create=True),
                         views._quiz_salt(self._Req(anon)))

    def test_two_users_see_different_arrangements(self):
        orders = {tuple(views._serve_options(dict(Q, id=qid), f'u{uid}'))
                  for uid in range(8) for qid in (1,)}
        self.assertGreater(len(orders), 1)
