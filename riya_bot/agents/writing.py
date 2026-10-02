from django.conf import settings
from .base import BaseAgent
from .utils import (
    fallback_text_module_analysis, analyze_text_with_sarvam_chat,
    merge_issues
)

class WritingAgent(BaseAgent):
    def __init__(self):
        super().__init__("writing")

    def run(self, payload):
        text = payload.get("text", "")
        api_key = settings.SARVAM_API_KEY
        non_space_chars = len("".join(str(text or "").split()))

        if not str(text or "").strip():
            raise ValueError("Please write something before analyzing.")
        if non_space_chars < 500:
            raise ValueError("Please write at least 500 characters before analyzing. Spaces are not counted.")
        if non_space_chars > 900:
            raise ValueError("Please keep your writing within 900 characters before analyzing. Spaces are not counted.")

        analysis = fallback_text_module_analysis("writing", text)
        fallback_issue_count = len(analysis.get("issues", []))

        if api_key:
            try:
                external = analyze_text_with_sarvam_chat(
                    "writing", text, "", 0, 0, api_key, language=payload.get("language", "english")
                )
                if external:
                    if external.get("scores"):
                        analysis["scores"].update(external["scores"])
                    if external.get("issues"):
                        # Ensure we prioritize AI issues but keep our safety fallback issues too
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
