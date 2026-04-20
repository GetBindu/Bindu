"""Joke Agent — port 3773.

Part of the gateway_test_fleet: five single-file agents deliberately
narrow in scope so the gateway's planner has to pick the right one for
each query. This one tells jokes.

Narrow instructions are intentional. We want the planner to fail cleanly
when asked to do something off-topic (e.g. "solve an equation") — not to
helpfully attempt the off-topic request and muddy the test signal.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 3773)
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

PORT = int(os.getenv("BINDU_PORT", "3773"))

agent = Agent(
    instructions=(
        "You are a joke-teller. You ONLY tell jokes. If the user asks "
        "anything that is not a joke request, politely say you only tell "
        "jokes and suggest a topic you could joke about instead."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
)


def handler(messages: list[dict[str, str]]):
    """Return a joke (or decline politely)."""
    return agent.run(input=messages)


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "joke_agent",
    "description": "Tells jokes on request. Declines anything else.",
    "deployment": {
        "url": f"http://localhost:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": [],
}


if __name__ == "__main__":
    bindufy(config, handler)
