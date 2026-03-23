"""Research agent — searches the web and answers questions about Bindu."""
from dotenv import load_dotenv
load_dotenv()
import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from bindu.penguin.bindufy import bindufy

model = OpenAIChat(
    id="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

research_agent = Agent(
    instructions="""
You are a research agent specialized in the Bindu AI Framework.
If the user asks about Bindu, assume they mean the Bindu AI framework
used for building interoperable AI agents.
Search and explain concepts like:
- Internet of Agents
- Bindu Framework
- Agent-to-Agent communication
- Bindu architecture
""",
    model=model,
    tools=[DuckDuckGoTools()],
)


def handler(messages: list[dict]) -> str:
    """Handle incoming messages and return research results."""
    query = messages[-1]["content"]
    result = research_agent.run(input=query)
    return result.content


config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "research_agent",
    "description": "Searches the web and answers questions using DuckDuckGo.",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": [],
}

if __name__ == "__main__":
    bindufy(config, handler)