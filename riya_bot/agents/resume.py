from .base import BaseAgent
from ..models import ResumeQuestion, ResumeAnswer
from ..resume_utils import evaluate_answer

class ResumeAgent(BaseAgent):
    def __init__(self):
        super().__init__("resume")

    def run(self, payload):
        action = payload.get("action")
        if action == "submit_answer":
            return self.submit_answer(payload)
        return {"error": "Invalid action"}

    def submit_answer(self, payload):
        question_id = payload.get("question_id")
        answer_text = payload.get("answer_text", "")
        session_id = payload.get("session_id")
        
        if not question_id or not session_id:
            raise ValueError("Missing question_id or session_id")

        question = ResumeQuestion.objects.get(id=question_id, session_id=session_id)
        eval_result = evaluate_answer(question.text, answer_text)
        
        ResumeAnswer.objects.update_or_create(
            question=question,
            defaults={
                'text': answer_text,
                'score': eval_result.get('score', 0),
                'feedback': eval_result.get('feedback', ''),
            },
        )
        return eval_result
