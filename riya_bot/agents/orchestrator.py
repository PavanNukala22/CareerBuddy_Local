from .resume import ResumeAgent
from .interview import InterviewAgent
from .speaking import SpeakingAgent
from .grammar import GrammarAgent
from .reading import ReadingAgent
from .writing import WritingAgent
from .listening import ListeningAgent
from .topic import TopicAgent
from .riya import RiyaAgent

class Orchestrator:
    def __init__(self):
        self.agents = {
            "resume": ResumeAgent(),
            "interview": InterviewAgent(),
            "speaking": SpeakingAgent(),
            "grammar": GrammarAgent(),
            "reading": ReadingAgent(),
            "writing": WritingAgent(),
            "listening": ListeningAgent(),
            "topic": TopicAgent(),
            "riya": RiyaAgent(),
        }

    def route(self, module_name, payload):
        agent = self.agents.get(module_name.lower())
        if not agent:
            return {
                "success": False,
                "data": {},
                "error": f"Agent for module '{module_name}' not found."
            }
        return agent.safe_run(payload)
