"""evaluate_answer must survive malformed model replies instead of scoring the
candidate 0 with a raw "Error: Could not parse JSON" message."""
from unittest import mock

from django.test import SimpleTestCase

from career_app import resume_utils
from career_app.resume_utils import _parse_evaluation, evaluate_answer

Q = 'What is a Python list?'
A = 'a list is an ordered mutable collection we can append and remove items'


class ParseEvaluationTests(SimpleTestCase):
    def test_valid_json(self):
        r = _parse_evaluation('{"score": 4, "feedback": "Good."}')
        self.assertEqual((r['score'], r['feedback']), (4, 'Good.'))

    def test_json_wrapped_in_prose_and_fences(self):
        r = _parse_evaluation('Here is my evaluation:\n```json\n{"score": 5, "feedback": "Correct."}\n```')
        self.assertEqual(r['score'], 5)

    def test_truncated_json_is_salvaged(self):
        r = _parse_evaluation('{"interpreted_answer": "A list is mutable.", "score": 5, "feedback": "The candidate corr')
        self.assertEqual(r['score'], '5')
        self.assertEqual(r['interpreted_answer'], 'A list is mutable.')
        self.assertTrue(r['feedback'].startswith('The candidate corr'))

    def test_unescaped_quotes_are_salvaged(self):
        r = _parse_evaluation('{"score": 3, "feedback": "Said "mutable" but no example."}')
        self.assertEqual(r['score'], '3')

    def test_no_score_at_all(self):
        self.assertIsNone(_parse_evaluation('I cannot evaluate this.'))


class EvaluateAnswerResilienceTests(SimpleTestCase):
    def test_retries_once_after_garbage(self):
        with mock.patch.object(resume_utils, '_sarvam_chat',
                               side_effect=['no json here', '{"score": 5, "feedback": "Correct."}']) as chat:
            r = evaluate_answer(Q, A)
        self.assertEqual(chat.call_count, 2)
        self.assertEqual(r['score'], 5)

    def test_truncated_reply_needs_no_retry(self):
        with mock.patch.object(resume_utils, '_sarvam_chat',
                               return_value='{"interpreted_answer": "A list is mutable.", "score": 4, "feedback": "Mostly') as chat:
            r = evaluate_answer(Q, A, spoken=True)
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(r['score'], 4)
        self.assertEqual(r['interpreted'], 'A list is mutable.')

    @mock.patch('time.sleep')
    def test_ai_unusable_still_gives_a_real_score(self, _sleep):
        with mock.patch.object(resume_utils, '_sarvam_chat', return_value='garbage') as chat:
            r = evaluate_answer(Q, A)
        self.assertEqual(chat.call_count, 4)          # full prompt x2, compact prompt x2
        self.assertIn(r['score'], range(6))
        self.assertTrue(r['feedback'])
        for word in ('Error', 'JSON', 'evaluate', 'automatically', 'parse'):
            self.assertNotIn(word, r['feedback'])

    @mock.patch('time.sleep')
    def test_service_down_still_gives_a_real_score(self, _sleep):
        with mock.patch.object(resume_utils, '_sarvam_chat', side_effect=Exception('timeout')):
            r = evaluate_answer(Q, A)
        self.assertIn(r['score'], range(6))
        self.assertNotIn('Error', r['feedback'])

    def test_compact_prompt_is_used_after_two_failures(self):
        replies = ['garbage', 'garbage', '{"score": 4, "feedback": "Good answer."}']
        with mock.patch.object(resume_utils, '_sarvam_chat', side_effect=replies) as chat:
            r = evaluate_answer(Q, A)
        self.assertEqual(r['score'], 4)
        self.assertIn('ONE line of JSON', chat.call_args_list[2][0][0])

    def test_empty_feedback_is_filled_in(self):
        with mock.patch.object(resume_utils, '_sarvam_chat', return_value='{"score": 5, "feedback": ""}'):
            r = evaluate_answer(Q, A)
        self.assertEqual(r['score'], 5)
        self.assertTrue(r['feedback'])


class LocalAnswerScoreTests(SimpleTestCase):
    Q = 'What is the difference between a list and a tuple in Python?'

    def test_on_topic_answer_scores_well(self):
        r = resume_utils._local_answer_score(
            self.Q, 'A list in Python is mutable so you can change it after creating it, while a tuple is '
                    'immutable and cannot be changed, which also makes a tuple slightly faster and hashable.',
            'python')
        self.assertGreaterEqual(r['score'], 3)

    def test_off_topic_answer_scores_zero(self):
        r = resume_utils._local_answer_score(
            self.Q, 'On the construction site I did slump tests and cube tests to check concrete quality.', 'python')
        self.assertEqual(r['score'], 0)

    def test_too_short(self):
        self.assertEqual(resume_utils._local_answer_score(self.Q, 'list tuple', 'python')['score'], 0)


class ScoreLadderTests(SimpleTestCase):
    """Every score 0-5 has a written test in the prompt, applied top-down, so the
    model is not left to guess where a good answer sits."""

    Q = 'What is the difference between a list and a tuple in Python?'
    CORRECT = ('A list in Python is mutable so you can change it after creating it, while a tuple is '
               'immutable and cannot be changed.')

    def _prompt_for(self, answer, topic='python'):
        with mock.patch.object(resume_utils, '_sarvam_chat',
                               return_value='{"score": 4, "feedback": "Correct."}') as chat:
            resume_utils.evaluate_answer(self.Q, answer, topic)
        return chat.call_args[0][0]

    def test_knowledge_ladder_defines_every_score(self):
        prompt = self._prompt_for(self.CORRECT)
        for band in ('5/5 -', '4/5 -', '3/5 -', '2/5 -', '1/5 -', '0/5 -'):
            self.assertIn(band, prompt)

    def test_knowledge_ladder_is_applied_top_down_with_a_tie_break(self):
        prompt = self._prompt_for(self.CORRECT)
        self.assertIn('award the FIRST score whose test passes, reading from 5 down', prompt)
        self.assertIn('give the LOWER one', prompt)

    def test_five_needs_depth_four_is_the_normal_good_answer(self):
        prompt = self._prompt_for(self.CORRECT)
        self.assertIn('DEPTH CONDITION', prompt)
        self.assertIn('This is the only way to score 5.', prompt)
        self.assertIn('The plain, correct, to-the-point answer lives here.', prompt)

    def test_never_deduct_and_never_award_lists_are_stated(self):
        prompt = self._prompt_for(self.CORRECT)
        self.assertIn('NEVER deduct for:', prompt)
        self.assertIn('NEVER award for:', prompt)

    def test_behavioural_ladder_defines_every_score(self):
        prompt = self._prompt_for('I fixed a broken report for my team last semester.', 'behavioural')
        for band in ('5 - S + A:', '4 - S only:', '3 - No specific situation',
                     '2 - Platitudes or opinions', '1 - On topic but says nothing gradable',
                     '0 - Nothing gradable at all'):
            self.assertIn(band, prompt)

    def test_behavioural_components_are_spelled_out(self):
        prompt = self._prompt_for('I fixed a broken report for my team last semester.', 'experience')
        for component in ('S (situation)', 'A (action)', 'R (result)'):
            self.assertIn(component, prompt)

    def test_result_does_not_change_the_behavioural_score(self):
        prompt = self._prompt_for('I fixed a broken report last semester.', 'behavioural')
        self.assertIn('it does NOT change the', prompt)
        self.assertIn('scores 5 whether or not R is there', prompt)

    def test_behavioural_scoring_is_components_only(self):
        prompt = self._prompt_for('I fixed a broken report last semester.', 'behavioural')
        self.assertIn('Do not add or remove', prompt)
        self.assertIn('points for anything outside S and A', prompt)

    def test_local_fallback_gives_four_for_a_plain_correct_answer(self):
        self.assertEqual(resume_utils._local_answer_score(self.Q, self.CORRECT, 'python')['score'], 4)

    def test_local_fallback_gives_five_for_a_fuller_answer(self):
        deep = (self.CORRECT + ' Because a tuple is immutable it can be hashed and used as a '
                'dictionary key, which a list cannot, and tuples are slightly faster to create, '
                'so I use a tuple for fixed records like coordinates and a list when the data grows.')
        self.assertEqual(resume_utils._local_answer_score(self.Q, deep, 'python')['score'], 5)


class LocalBehaviouralLadderTests(SimpleTestCase):
    """Offline scorer (AI service down) must follow the same S/A ladder."""

    def score(self, text):
        return resume_utils._local_hr_answer_score(text)['score']

    def test_situation_and_action_is_five(self):
        self.assertEqual(self.score(
            'Last year in my college project our team missed a deadline, so I rewrote the '
            'report myself and we submitted it on time.'), 5)

    def test_result_is_not_required_for_five(self):
        self.assertEqual(self.score(
            'During my internship a client order was wrong. I called the supplier and '
            'checked the invoice.'), 5)

    def test_situation_without_own_action_is_four(self):
        self.assertEqual(self.score(
            'Last year there was a big audit at our site and the whole team was under '
            'pressure for two weeks.'), 4)

    def test_usual_practice_is_three(self):
        self.assertEqual(self.score(
            'I usually handle it by listening to both sides and then deciding what is fair '
            'for everyone.'), 3)

    def test_hypothetical_with_concrete_actions_is_three(self):
        self.assertEqual(self.score(
            'If there is a conflict I would talk to each person separately and then agree on '
            'a plan together.'), 3)

    def test_platitude_is_two(self):
        self.assertEqual(self.score(
            'Teamwork is important because people should always communicate clearly at work.'), 2)

    def test_bare_acknowledgement_is_one(self):
        self.assertEqual(self.score('Yes, I have done that.'), 1)
        self.assertEqual(self.score('It was fine.'), 1)

    def test_refusal_and_blank_are_zero(self):
        for text in ("I don't know", 'no idea', '', '   '):
            self.assertEqual(self.score(text), 0, text)
