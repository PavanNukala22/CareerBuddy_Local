import logging
from django.conf import settings
from .base import BaseAgent
from .utils import (
    fallback_text_module_analysis, analyze_text_with_sarvam_chat,
    merge_issues, has_meaningful_speech, normalise_score_scale
)

logger = logging.getLogger(__name__)

class ListeningAgent(BaseAgent):
    def __init__(self):
        super().__init__("listening")

    def run(self, payload):
        text = payload.get("text", "")
        reference_text = payload.get("reference_text", "")
        duration_seconds = payload.get("duration_seconds", 0)
        pause_count = payload.get("pause_count", 0)
        api_key = settings.SARVAM_API_KEY

        if not has_meaningful_speech(text):
            raise ValueError("Please provide a longer listening response.")

        analysis = fallback_text_module_analysis("listening", text, reference_text, duration_seconds, pause_count)

        if api_key:
            try:
                external = analyze_text_with_sarvam_chat(
                    "listening", text, reference_text, duration_seconds, pause_count, api_key
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
                logger.error("listening AI analysis failed, using offline fallback: %s", exc)

        return {
            "text": text,
            "issues": analysis["issues"],
            "improved_passage": analysis["improved_passage"],
            "scores": analysis["scores"],
            "feedback": analysis.get("feedback"),
            "quick_tip": analysis.get("quick_tip")
        }
