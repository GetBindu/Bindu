"""Joke Agent — port 5773.

Part of the gateway_test_fleet: five single-file agents deliberately
narrow in scope so the gateway's planner has to pick the right one for
each query. This one tells jokes.

Narrow instructions are intentional. We want the planner to fail cleanly
when asked to do something off-topic (e.g. "solve an equation") — not to
helpfully attempt the off-topic request and muddy the test signal.

Port: 5xxx range is reserved for agents (3xxx is infra — comms UI on
3775, comms-api on 3787, gateway on 3774). Fleet map: 5773 joke_agent,
5775 math, 5776 poet, 5777 research, 5778 bindu_docs.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 5773)
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

PORT = int(os.getenv("BINDU_PORT", "5773"))

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
    return agent.run(input=messages).content


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "joke_agent",
    "description": "Tells jokes on request. Declines anything else.",
    "deployment": {
        # https + 127.0.0.1: matches what bindu actually serves when
        # MTLS__ENABLED=true (peers fetching /.well-known/agent.json
        # would otherwise see http://localhost and fail to reach back).
        "url": f"https://127.0.0.1:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173", "http://localhost:3775"],
    },
    "capabilities": {"push_notifications": True},
    "global_webhook_url": "http://127.0.0.1:3787/webhooks/bindu/joke_agent",
    "skills": [
        {
            "id": "tell_joke",
            "name": "Tell a joke",
            "description": (
                "Return a short, lighthearted joke on any topic the "
                "user requests. Declines politely for off-limits "
                "subjects (e.g., medical, legal, sensitive)."
            ),
            "tags": ["humor", "joke", "entertainment"],
            "examples": ["Tell me a programmer joke", "Make me laugh"],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
        }
    ],
}


if __name__ == "__main__":
    bindufy(config, handler)
