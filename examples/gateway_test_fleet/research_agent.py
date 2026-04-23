"""Research Agent — port 3777.

Part of the gateway_test_fleet. Adapted from examples/beginner/
agno_simple_example.py to run on a distinct port with the fleet's
author tag. Uses DuckDuckGo for web search.

Kept close to the original so this agent exercises the SAME code path
a real user would hit — adapting only what's necessary for parallel
operation in the test fleet.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 3777)
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

PORT = int(os.getenv("BINDU_PORT", "3777"))

agent = Agent(
    instructions=(
        "You are a research assistant that finds and summarizes "
        "information. Use web search to back up your answers and cite "
        "the sources you used."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
)


def handler(messages: list[dict[str, str]]):
    """Run the agent against the conversation history."""
    return agent.run(input=messages)


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "research_agent",
    "description": "Researches topics via web search and summarizes findings.",
    "deployment": {
        "url": f"http://localhost:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": [],
}


if __name__ == "__main__":
    bindufy(config, handler)
