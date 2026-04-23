"""Math Agent — port 3775.

Part of the gateway_test_fleet. Solves math problems step-by-step,
refuses non-math requests. Narrow scope is deliberate: the gateway's
planner must distinguish this agent's competence from the others in
the fleet when routing queries.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 3775)
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

PORT = int(os.getenv("BINDU_PORT", "3775"))

agent = Agent(
    instructions=(
        "You are a math problem solver. You ONLY answer math questions "
        "(arithmetic, algebra, calculus, geometry, statistics). Show "
        "your work step by step. If the user asks anything non-math, "
        "politely decline and say you only handle math problems."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
)


def handler(messages: list[dict[str, str]]):
    """Solve math problems step-by-step."""
    return agent.run(input=messages)


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "math_agent",
    "description": "Solves math problems step-by-step. Declines anything else.",
    "deployment": {
        "url": f"http://localhost:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": [],
}


if __name__ == "__main__":
    bindufy(config, handler)
