"""
Orchestrator

Coordinates agent discovery and execution.
"""

from router_agent import RouterAgent
from skill_registry import SkillRegistry

from research_agent import ResearchAgent
from summarizer_agent import SummarizerAgent
from translator_agent import TranslatorAgent


class Orchestrator:

    def __init__(self):

        self.registry = SkillRegistry()

        # initialize agents
        self.research_agent = ResearchAgent()
        self.summarizer_agent = SummarizerAgent()
        self.translator_agent = TranslatorAgent()

        # register agents dynamically
        self.registry.register_agent("research_agent", ["research", "explain"])
        self.registry.register_agent("summarizer_agent", ["summarize"])
        self.registry.register_agent("translator_agent", ["translate"])

        self.router = RouterAgent(self.registry)

        self.agents = {
            "research_agent": self.research_agent,
            "summarizer_agent": self.summarizer_agent,
            "translator_agent": self.translator_agent,
        }

    async def run(self, request: str):

        agent_name = self.router.route(request)

        if not agent_name:
            return "No suitable agent found."

        agent = self.agents.get(agent_name)

        return await agent.run(request)