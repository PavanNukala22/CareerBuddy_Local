from .speaking import SpeakingAgent
from .reading import ReadingAgent
from .writing import WritingAgent
from .listening import ListeningAgent

class Orchestrator:
    def __init__(self):
        self.agents = {
            "speaking": SpeakingAgent(),
            "reading": ReadingAgent(),
            "writing": WritingAgent(),
            "listening": ListeningAgent(),
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
