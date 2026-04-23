"""Poet Agent — port 3776.

Part of the gateway_test_fleet. Writes short poems (4-line max) on a
given topic. Narrow scope so the planner has to pick it specifically
when the user wants creative verse.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 3776)
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

PORT = int(os.getenv("BINDU_PORT", "3776"))

agent = Agent(
    instructions=(
        "You are a poet. You ONLY write short poems (maximum 4 lines) "
        "on topics the user suggests. If the user asks for anything "
        "that is not a poem request, politely decline and say you only "
        "write poems."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
)


def handler(messages: list[dict[str, str]]):
    """Write a short poem (or decline politely)."""
    return agent.run(input=messages)


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "poet_agent",
    "description": "Writes short poems (max 4 lines). Declines anything else.",
    "deployment": {
        "url": f"http://localhost:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": [],
}


if __name__ == "__main__":
    bindufy(config, handler)
