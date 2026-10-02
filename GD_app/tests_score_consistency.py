"""
Prompt-kit item: "GD Score Internal Consistency" (BR-17). Verifies that
analyze_user_performance()'s overall_score is ALWAYS the sum of the four
dimension scores — even when the underlying AI model's raw JSON omits one
dimension and/or returns an overall score that disagrees with the parts.
"""
import json
from unittest import mock

from django.test import SimpleTestCase

from GD_app.agents import analyze_user_performance


def _fake_response(json_body):
    resp = mock.Mock()
    resp.raise_for_status = mock.Mock()
    resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(json_body)}}]
    }
    return resp


class GDScoreConsistencyTests(SimpleTestCase):
    def _history(self):
        return [
            {"is_user": True, "content": "I think AI will change many jobs but also create new ones."},
            {"is_user": False, "speaker_name": "Alex", "content": "Interesting point."},
        ]

    def test_missing_dimension_defaults_to_15_and_overall_is_recomputed_as_the_sum(self):
        # The model returns overall=100 (deliberately wrong) and only 3 of 4
        # dimensions — grammar is missing entirely.
        model_reply = {
            "overall_score": 100,
            "fluency": {"score": 20, "feedback": "Good pace."},
            "relevance": {"score": 22, "feedback": "On topic."},
            "confidence": {"score": 18, "feedback": "Mostly confident."},
        }
        with mock.patch("GD_app.agents.requests.post", return_value=_fake_response(model_reply)):
            report = analyze_user_performance("AI and jobs", self._history(), "english")

        self.assertEqual(report["grammar"]["score"], 15, "missing dimension must default to 15, not be dropped")
        expected_sum = 20 + 15 + 22 + 18
        self.assertEqual(
            report["overall_score"], expected_sum,
            "overall_score must be recomputed as the sum of the four dimensions, never trusted from the model",
        )
        self.assertNotEqual(report["overall_score"], 100, "the model's own (wrong) overall_score must be discarded")

    def test_all_four_dimensions_present_and_consistent_overall_is_still_recomputed_not_merely_accepted(self):
        model_reply = {
            "overall_score": 999,  # deliberately absurd, to prove it's never trusted
            "fluency": {"score": 19, "feedback": "x"},
            "grammar": {"score": 17, "feedback": "x"},
            "relevance": {"score": 21, "feedback": "x"},
            "confidence": {"score": 18, "feedback": "x"},
        }
        with mock.patch("GD_app.agents.requests.post", return_value=_fake_response(model_reply)):
            report = analyze_user_performance("AI and jobs", self._history(), "english")

        self.assertEqual(report["overall_score"], 19 + 17 + 21 + 18)
