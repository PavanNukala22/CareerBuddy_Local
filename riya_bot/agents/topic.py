from django.conf import settings
from .base import BaseAgent
from .utils import (
    get_topic_practice_config, fallback_topic_practice, 
    topic_practice_with_sarvam_chat
)

class TopicAgent(BaseAgent):
    def __init__(self):
        super().__init__("topic")

    def run(self, payload):
        topic_slug = payload.get("topic")
        prompt = payload.get("prompt", "")
        
        topic = get_topic_practice_config(topic_slug)
        if not topic:
            raise ValueError(f"Invalid topic: {topic_slug}")

        result = fallback_topic_practice(topic, prompt)
        api_key = settings.SARVAM_API_KEY
        
        if api_key:
            try:
                # In a real implementation, we'd port the full logic here
                pass
            except Exception:
                pass

        return {
            "topic": topic["slug"],
            "used_prompt": prompt or topic["default_prompt"],
            "result": result,
        }
