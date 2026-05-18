"""Math Agent — port 5775.

Part of the gateway_test_fleet. Solves math problems step-by-step,
refuses non-math requests. Narrow scope is deliberate: the gateway's
planner must distinguish this agent's competence from the others in
the fleet when routing queries.

Port note: 3xxx is reserved for infra (comms UI on 3775, comms-api
on 3787, gateway on 3774, gateway2 on 3779). All agents live above
5000 so the two ranges can't collide. Fleet map:
    5773  joke_agent
    5775  math_agent  ← here
    5776  poet_agent
    5777  research_agent
    5778  bindu_docs_agent

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 5775)
"""

import os

from dotenv import load_dotenv

# Load .env BEFORE importing bindu — `bindu.settings:app_settings = Settings()`
# is constructed at module-import time, so any MTLS__/AUTH__/HYDRA__ vars set
# by a later load_dotenv land in os.environ but never reach the singleton.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agno.agent import Agent  # noqa: E402
from agno.models.openrouter import OpenRouter  # noqa: E402

from bindu.penguin.bindufy import bindufy  # noqa: E402

PORT = int(os.getenv("BINDU_PORT", "5775"))

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
    return agent.run(input=messages).content


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "math_agent",
    "description": "Solves math problems step-by-step. Declines anything else.",
    "deployment": {
        # https + 127.0.0.1: matches what bindu actually serves when
        # MTLS__ENABLED=true (peers fetching /.well-known/agent.json
        # would otherwise see http://localhost and fail to reach back).
        "url": f"https://127.0.0.1:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173", "http://localhost:3775"],
    },
    "capabilities": {"push_notifications": True},
    "global_webhook_url": "http://127.0.0.1:3787/webhooks/bindu/math_agent",
    "skills": [
        {
            "id": "solve_math",
            "name": "Solve math problems",
            "description": (
                "Solve arithmetic, algebra, calculus, and word "
                "problems step-by-step. Shows the working, not just "
                "the answer."
            ),
            "tags": ["math", "arithmetic", "algebra", "calculus"],
            "examples": [
                "What's 17 * 23?",
                "Solve x^2 + 4x + 3 = 0",
                "Differentiate sin(x)*cos(x)",
            ],
            "input_modes": ["text/plain"],
            "output_modes": ["text/markdown"],
        }
    ],
}


if __name__ == "__main__":
    bindufy(config, handler)
