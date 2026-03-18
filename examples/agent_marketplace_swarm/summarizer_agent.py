"""
Summarizer Agent
"""

from agno.agent import Agent
from agno.models.openrouter import OpenRouter


class SummarizerAgent:

    def __init__(self):
        self.agent = Agent(
            model=OpenRouter(id="openai/gpt-oss-120b"),
            instructions="Summarize the given text clearly and concisely.",
        )

    async def run(self, text: str):
        response = self.agent.run(text)
        return response.content