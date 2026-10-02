from .base import BaseAgent

class InterviewAgent(BaseAgent):
    def __init__(self):
        super().__init__("interview")

    def run(self, payload):
        from career_app.models import FAQQuestion
        from .utils import (
            analyze_text_with_sarvam_chat, fallback_text_module_analysis,
            merge_issues
        )
        from django.conf import settings
        import random

        text = payload.get("text")
        if text:
            # Handle analysis
            duration_seconds = payload.get("duration_seconds", 0)
            pause_count = payload.get("pause_count", 0)
            reference_text = payload.get("reference_text", "")
            api_key = settings.SARVAM_API_KEY
            
            analysis = fallback_text_module_analysis("interview", text, reference_text, duration_seconds, pause_count)
            fallback_issue_count = len(analysis.get("issues", []))
            
            if api_key:
                try:
                    external = analyze_text_with_sarvam_chat(
                        "interview", text, reference_text, duration_seconds, pause_count, api_key
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
            return analysis

        # Handle chat (fetching a question)
        role = payload.get("role", "Software Engineer").lower()
        topics = FAQQuestion.objects.values_list('topic', flat=True).distinct()
        matched_topic = None
        for t in topics:
            if t in role:
                matched_topic = t
                break
        
        if matched_topic:
            qs = FAQQuestion.objects.filter(topic=matched_topic)
        else:
            qs = FAQQuestion.objects.all()

        if qs.exists():
            question = random.choice(qs)
            reply = question.question_text
        else:
            reply = "Could you tell me about your background and experience?"

        return {
            "reply": reply,
            "question_index": payload.get("question_index", 0),
            "done": False
        }
