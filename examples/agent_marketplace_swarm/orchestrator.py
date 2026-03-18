"""
Orchestrator

Coordinates agent discovery and execution.
"""

from router_agent import RouterAgent
from summarizer_agent import SummarizerAgent
from translator_agent import TranslatorAgent


class Orchestrator:

    def __init__(self):

        self.router = RouterAgent()

        self.agents = {
            "summarizer_agent": SummarizerAgent(),
            "translator_agent": TranslatorAgent(),
        }

    async def run(self, request: str):

        agent_name = self.router.route(request)

        if not agent_name:
            return "No suitable agent found."

        agent = self.agents.get(agent_name)

        return await agent.run(request)