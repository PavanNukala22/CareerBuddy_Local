from django.conf import settings
from .base import BaseAgent
from .utils import (
    transcribe_with_sarvam, fallback_text_module_analysis, 
    analyze_text_with_sarvam_chat, merge_issues, has_meaningful_speech,
    choose_best_transcript
)

class ReadingAgent(BaseAgent):
    def __init__(self):
        super().__init__("reading")

    def run(self, payload):
        text = payload.get("text", "")
        client_transcript = payload.get("client_transcript", "")
        reference_text = payload.get("reference_text", "")
        audio_file = payload.get("audio")
        api_key = settings.SARVAM_API_KEY

        duration_seconds = float(payload.get("duration_seconds", 0))
        pause_count = int(payload.get("pause_count", 0))

        stt_text = ""
        if audio_file and api_key:
            stt_text, _, _ = transcribe_with_sarvam(audio_file, api_key)

        text = choose_best_transcript([text, client_transcript, stt_text], reference_text)

        if not has_meaningful_speech(text):
            raise ValueError("Please provide a longer reading response.")

        analysis = fallback_text_module_analysis("reading", text, reference_text, duration_seconds, pause_count)
        fallback_issue_count = len(analysis.get("issues", []))

        if api_key:
            try:
                external = analyze_text_with_sarvam_chat(
                    "reading", text, reference_text, duration_seconds, pause_count, api_key
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
        
        # In reading, we want to highlight mistakes on the ORIGINAL passage
        # so the user sees where they made mistakes relative to the text.
        return {
            "text": reference_text or text,
            "issues": analysis["issues"],
            "improved_passage": analysis["improved_passage"],
            "scores": analysis["scores"],
            "feedback": analysis.get("feedback"),
            "quick_tip": analysis.get("quick_tip"),
            "user_transcript": text
        }
