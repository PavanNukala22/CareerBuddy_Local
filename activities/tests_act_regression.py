"""Regression set from CareerBuddy_Activities_AI_Bug_Report (TC-ACT-R1..R7).

Guards the BUG-ACT-01..07 fixes in the Activities AI path. No test here makes a
real network call — the Sarvam/LanguageTool `requests.post` is always mocked.
"""

import json
import logging
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .agents import utils
from .tests_aim import AIMTestDataMixin


CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"


def _fake_chat_response(payload_dict):
    """A requests-like response echoing a Sarvam chat completion."""
    resp = mock.Mock()
    resp.raise_for_status = mock.Mock()
    resp.json = mock.Mock(return_value={
        "choices": [{"message": {"content": json.dumps(payload_dict)}}]
    })
    return resp


def _route_post(chat_payload=None, chat_error=None):
    """Build a requests.post side_effect that routes by URL.

    LanguageTool calls get an empty match set; the Sarvam chat URL gets
    `chat_payload` (or raises `chat_error`). Captures the chat calls seen.
    """
    seen = {"chat_urls": []}

    def _side_effect(url, *args, **kwargs):
        if "languagetool" in url:
            r = mock.Mock()
            r.raise_for_status = mock.Mock()
            r.json = mock.Mock(return_value={"matches": []})
            return r
        if "chat/completions" in url:
            seen["chat_urls"].append(url)
            if chat_error is not None:
                raise chat_error
            return _fake_chat_response(chat_payload or {})
        r = mock.Mock()
        r.raise_for_status = mock.Mock()
        r.json = mock.Mock(return_value={})
        return r

    return _side_effect, seen


@override_settings(SARVAM_API_KEY="test-key", LANGUAGETOOL_API_URL="")
class ActivitiesAIRegressionTests(AIMTestDataMixin, TestCase):

    # -- TC-ACT-R1: writing hits /v1 and returns the AI-sourced correction ----
    def test_r1_writing_calls_v1_and_returns_ai_issue(self):
        user = self.make_user("r1")
        self.client.force_login(user)
        ai = {
            "scores": {"grammar": 70, "overall": 72},
            "issues": [{"phrase": "freind", "type": "Spelling",
                        "message": "Incorrect spelling.", "suggestion": "friend"}],
            "improved_passage": "My friend is kind.",
            "feedback": "Reviewed.", "quick_tip": "Proofread.",
        }
        side_effect, seen = _route_post(chat_payload=ai)
        essay = "My freind is kind and honest. " * 30  # 720 non-space chars, in range
        with mock.patch("activities.agents.utils.requests.post", side_effect=side_effect):
            resp = self.client.post(
                reverse("analyze_writing", args=[self.speaking_ex.pk]),
                {"text": essay, "language": "english"},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(seen["chat_urls"], "no outbound chat call was made")
        for url in seen["chat_urls"]:
            self.assertTrue(url.endswith("/v1/chat/completions"), url)
        issues = resp.json()["data"]["issues"]
        self.assertTrue(any(i.get("phrase") == "freind" and i.get("suggestion") == "friend"
                            for i in issues), issues)

    # -- TC-ACT-R2: speaking hits /v1 and returns AI scores/issues ------------
    def test_r2_speaking_calls_v1_and_returns_ai_scores(self):
        user = self.make_user("r2")
        self.client.force_login(user)
        ai = {
            "scores": {"fluency": 80, "grammar": 70, "overall": 78},
            "issues": [{"phrase": "i have problem", "type": "Grammar",
                        "message": "Article/number.", "suggestion": "I have a problem"}],
            "improved_passage": "I have a problem.", "feedback": "Reviewed.", "quick_tip": "Slow down.",
        }
        side_effect, seen = _route_post(chat_payload=ai)
        with mock.patch("activities.agents.utils.requests.post", side_effect=side_effect):
            resp = self.client.post(
                reverse("analyze_speaking", args=[self.speaking_ex.pk]),
                {"client_transcript": "so i have problem when i go to school and i really likes it",
                 "duration_seconds": "40", "pause_count": "1"},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(seen["chat_urls"], "no outbound chat call was made")
        for url in seen["chat_urls"]:
            self.assertTrue(url.endswith("/v1/chat/completions"), url)
        data = resp.json()["data"]
        self.assertIn("overall", data["scores"])
        self.assertTrue(data["issues"])

    # -- TC-ACT-R3: the chat URL is the same /v1 URL used repo-wide ----------
    def test_r3_chat_url_is_v1(self):
        self.assertEqual(utils.SARVAM_CHAT_URL, CHAT_URL)

    # -- TC-ACT-R4: a chat 404/500 is logged at error level (BUG-ACT-02/03) --
    def test_r4_chat_failure_is_logged_and_degrades_gracefully(self):
        user = self.make_user("r4")
        self.client.force_login(user)
        side_effect, _ = _route_post(chat_error=RuntimeError("404 Not Found"))
        essay = "My freind is kind and honest. " * 30
        with mock.patch("activities.agents.utils.requests.post", side_effect=side_effect):
            with self.assertLogs("activities.agents.writing", level="ERROR") as logs:
                resp = self.client.post(
                    reverse("analyze_writing", args=[self.speaking_ex.pk]),
                    {"text": essay, "language": "english"},
                )
        # AS-02: still completes on the offline fallback, but the fault is now visible.
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])
        self.assertTrue(any("AI analysis failed" in m for m in logs.output), logs.output)

    # -- TC-ACT-R5: writing guard messages (learner-facing) ------------------
    def test_r5_writing_validation_messages(self):
        user = self.make_user("r5")
        self.client.force_login(user)
        for text in ["", "too short", "x" * 1200]:
            resp = self.client.post(
                reverse("analyze_writing", args=[self.speaking_ex.pk]), {"text": text})
            error = resp.json()["error"]
            self.assertNotIn("Internal agent error", error)
            self.assertTrue(error.startswith("Please"), error)

    # -- TC-ACT-R6: STT fault is surfaced, not blamed on the recording -------
    def test_r6_stt_failure_surfaces_service_error(self):
        user = self.make_user("r6")
        self.client.force_login(user)
        audio = SimpleUploadedFile("a.webm", b"\x00" * 64, content_type="audio/webm")
        with mock.patch("activities.agents.speaking.transcribe_with_sarvam",
                        return_value=("", {}, {"message": "stt down", "status": 500})):
            resp = self.client.post(
                reverse("analyze_speaking", args=[self.speaking_ex.pk]),
                {"audio": audio, "client_transcript": "", "duration_seconds": "5", "pause_count": "0"},
            )
        self.assertEqual(resp.status_code, 200)
        error = resp.json()["error"] or ""
        self.assertIn("transcription service", error.lower())
        self.assertNotIn("No meaningful speech", error)

    # -- BUG-ACT-06: the AI narrative is not overridden by heuristics --------
    def test_ai_narrative_wins_over_heuristics(self):
        user = self.make_user("narrative")
        self.client.force_login(user)
        ai = {
            "scores": {"grammar": 70, "overall": 72},
            "issues": [{"phrase": "freind", "type": "Spelling",
                        "message": "x", "suggestion": "friend"}],
            "improved_passage": "AI CORRECTED PASSAGE.",
            "feedback": "AI FEEDBACK.", "quick_tip": "AI TIP.",
        }
        side_effect, _ = _route_post(chat_payload=ai)
        essay = "My freind is kind and honest. " * 30
        with mock.patch("activities.agents.utils.requests.post", side_effect=side_effect):
            resp = self.client.post(
                reverse("analyze_writing", args=[self.speaking_ex.pk]),
                {"text": essay, "language": "english"},
            )
        data = resp.json()["data"]
        self.assertEqual(data["improved_passage"], "AI CORRECTED PASSAGE.")
        self.assertEqual(data["feedback"], "AI FEEDBACK.")

    # -- BUG-ACT-07: no non-standard reasoning_effort field is sent ----------
    def test_no_reasoning_effort_field_in_chat_payload(self):
        captured = {}

        def _capture(url, *args, **kwargs):
            if "chat/completions" in url:
                captured["json"] = kwargs.get("json", {})
                return _fake_chat_response({"scores": {}, "issues": []})
            r = mock.Mock(); r.raise_for_status = mock.Mock(); r.json = mock.Mock(return_value={"matches": []})
            return r

        with mock.patch("activities.agents.utils.requests.post", side_effect=_capture):
            utils.analyze_text_with_sarvam_chat("writing", "hello world", "", 0, 0, "k")
        self.assertIn("json", captured)
        self.assertNotIn("reasoning_effort", captured["json"])
