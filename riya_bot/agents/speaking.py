import re
import requests
from django.conf import settings
from .base import BaseAgent
from .utils import (
    transcribe_with_sarvam, clamp_score, merge_issues, 
    has_meaningful_speech, fallback_text_module_analysis,
    choose_best_transcript,
    analyze_text_with_sarvam_chat,
    derive_revision_issues,
)

class SpeakingAgent(BaseAgent):
    def __init__(self):
        super().__init__("speaking")

    def run(self, payload):
        audio_file = payload.get("audio")
        duration_seconds = payload.get("duration_seconds", 0)
        pause_count = payload.get("pause_count", 0)
        client_transcript = payload.get("client_transcript", "")
        reference_text = payload.get("reference_text", "")
        api_key = settings.SARVAM_API_KEY

        stt_text = ""
        if audio_file and api_key:
            stt_text, _, _ = transcribe_with_sarvam(audio_file, api_key)

        transcript = choose_best_transcript([stt_text, client_transcript], reference_text)

        if not transcript:
            raise ValueError("No meaningful speech detected. Please record and speak clearly, then analyze again.")

        analysis = fallback_text_module_analysis("speaking", transcript, "", duration_seconds, pause_count)
        fallback_issue_count = len(analysis.get("issues", []))

        if api_key:
            try:
                external = analyze_text_with_sarvam_chat(
                    "speaking", transcript, "", duration_seconds, pause_count, api_key
                )
                if external:
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

        derived_issues = derive_revision_issues(transcript, analysis.get("improved_passage", ""))
        if derived_issues:
            analysis["issues"] = merge_issues(analysis["issues"], derived_issues)

        final_scores = analysis["scores"]
        if "grammar" not in final_scores:
            issue_penalty = len(analysis.get("issues", [])) * 5
            final_scores["grammar"] = max(60, clamp_score(95 - issue_penalty))
        
        if "overall" not in final_scores:
            vals = [v for k, v in final_scores.items() if isinstance(v, (int, float))]
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
