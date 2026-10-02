from django.conf import settings
from .base import BaseAgent
from .utils import (
    fallback_text_module_analysis, analyze_text_with_sarvam_chat, 
    merge_issues, has_meaningful_speech
)

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
        fallback_issue_count = len(analysis.get("issues", []))

        if api_key:
            try:
                external = analyze_text_with_sarvam_chat(
                    "listening", text, reference_text, duration_seconds, pause_count, api_key
                )
                if external.get("scores"):
                    analysis["scores"].update(external["scores"])
                if external.get("issues"):
                    analysis["issues"] = merge_issues(external["issues"], analysis["issues"])
                external_issue_count = len(external.get("issues", []))
                prefer_external_narrative = not fallback_issue_count or external_issue_count >= fallback_issue_count
                if external.get("improved_passage") and prefer_external_narrative:
                    analysis["improved_passage"] = external["improved_passage"]
                if external.get("feedback") and prefer_external_narrative:
                    analysis["feedback"] = external["feedback"]
                if external.get("quick_tip") and prefer_external_narrative:
                    analysis["quick_tip"] = external["quick_tip"]
            except Exception:
                pass

        return {
            "text": text,
            "issues": analysis["issues"],
            "improved_passage": analysis["improved_passage"],
            "scores": analysis["scores"],
            "feedback": analysis.get("feedback"),
            "quick_tip": analysis.get("quick_tip")
        }
