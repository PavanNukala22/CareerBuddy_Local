from .base import BaseAgent

class GrammarAgent(BaseAgent):
    def __init__(self):
        super().__init__("grammar")

    def run(self, payload):
        return {"status": "Grammar analysis completed"}
