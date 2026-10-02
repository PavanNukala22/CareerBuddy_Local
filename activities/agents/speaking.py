import logging
import re
import requests
from django.conf import settings
from .base import BaseAgent, AgentInputError
from .utils import (
    transcribe_with_sarvam, clamp_score, merge_issues,
    has_meaningful_speech, fallback_text_module_analysis,
    choose_best_transcript,
    analyze_text_with_sarvam_chat,
    derive_revision_issues, normalise_score_scale,
)

logger = logging.getLogger(__name__)

class SpeakingAgent(BaseAgent):
    def __init__(self):
        super().__init__("speaking")

    def run(self, payload):
        audio_file = payload.get("audio")
        duration_seconds = payload.get("duration_seconds", 0)
        pause_count = payload.get("pause_count", 0)
        client_transcript = payload.get("client_transcript", "")
        api_key = settings.SARVAM_API_KEY

        reference_text = payload.get("reference_text", "")
        stt_text = ""
        stt_error = None
        if audio_file and api_key:
            stt_text, _, stt_error = transcribe_with_sarvam(audio_file, api_key, prompt=reference_text)

        transcript = choose_best_transcript([stt_text, client_transcript], reference_text)

        if not transcript:
            # BUG-ACT-05: a transcription-service fault is not the learner's fault.
            # Only blame the recording when STT actually ran without error.
            if stt_error and not str(client_transcript or "").strip():
                logger.error("speaking STT failed: %s", stt_error.get("message"))
                raise RuntimeError("The speech transcription service is temporarily unavailable. Please try again shortly.")
            raise AgentInputError("No meaningful speech detected. Please record and speak clearly, then analyze again.")

        analysis = fallback_text_module_analysis("speaking", transcript, "", duration_seconds, pause_count)

        if api_key:
            try:
                # payload["language"] was already being sent by the frontend
                # (formData.append("language", ...) in speaking.js) but was
                # never read here, so the dropdown had no effect on the AI
                # feedback text — only on the page's own static labels.
                external = analyze_text_with_sarvam_chat(
                    "speaking", transcript, "", duration_seconds, pause_count, api_key,
                    language=payload.get("language", "english"),
                )
                if external:
                    if external.get("scores"):
                        analysis["scores"].update(normalise_score_scale(external["scores"]))
                    if external.get("issues"):
                        analysis["issues"] = merge_issues(external["issues"], analysis["issues"])
                    # BUG-ACT-06: prefer the AI narrative whenever the call succeeds.
                    if external.get("improved_passage"):
                        analysis["improved_passage"] = external["improved_passage"]
                    if external.get("feedback"):
                        analysis["feedback"] = external["feedback"]
                    if external.get("quick_tip"):
                        analysis["quick_tip"] = external["quick_tip"]
            except Exception as exc:
                logger.error("speaking AI analysis failed, using offline fallback: %s", exc)

        derived_issues = derive_revision_issues(transcript, analysis.get("improved_passage", ""))
        if derived_issues:
            analysis["issues"] = merge_issues(analysis["issues"], derived_issues)

        # Ensure all score keys exist for the UI
        final_scores = analysis["scores"]
        if "grammar" not in final_scores:
            # Estimate grammar based on issue count (starting at 95)
            issue_penalty = len(analysis.get("issues", [])) * 5
            final_scores["grammar"] = clamp_score(max(60, 95 - issue_penalty), 60)

        if "overall" not in final_scores:
            # Average only the core quality scores that reflect language ability.
            # Exclude 'relevance' (handled as a cap in views.py) and heuristic
            # fallbacks like 'confidence' and 'pronunciation' which are not direct
            # indicators of speaking quality when returned by the AI.
            QUALITY_KEYS = {"fluency", "grammar", "vocabulary", "clarity"}
            quality_vals = [
                v for k, v in final_scores.items()
                if k in QUALITY_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            if quality_vals:
                final_scores["overall"] = round(sum(quality_vals) / len(quality_vals))
            else:
                # No quality scores at all — fall back to averaging everything
                # except relevance so an off-topic penalty doesn't silently halve
                # a score that was already capped separately.
                vals = [
                    v for k, v in final_scores.items()
                    if k != "relevance" and isinstance(v, (int, float)) and not isinstance(v, bool)
                ]
                final_scores["overall"] = round(sum(vals) / len(vals)) if vals else 75

        return {
            "text": transcript,
            "transcript": transcript,
            "issues": analysis["issues"],
            "improved_passage": analysis["improved_passage"],
            "scores": analysis["scores"],
            "duration_seconds": round(duration_seconds, 2),
            "pause_count": pause_count,
            "feedback": analysis.get("feedback"),
            "quick_tip": analysis.get("quick_tip")
        }
