"""Poet Agent — port 5776.

Part of the gateway_test_fleet. Writes short poems (4-line max) on a
given topic. Narrow scope so the planner has to pick it specifically
when the user wants creative verse.

Port: 5xxx range for agents (3xxx is infra). Fleet map: 5773 joke,
5775 math, 5776 poet ← here, 5777 research, 5778 bindu_docs.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 5776)
"""

import os

from dotenv import load_dotenv

# Per-agent override: this agent demos Hydra-protected calls even when
# the shared examples/.env keeps AUTH__ENABLED=false for the rest of the
# fleet. Set BEFORE load_dotenv — python-dotenv defaults to
# override=False, so already-set env vars survive.
os.environ["AUTH__ENABLED"] = "true"
os.environ.setdefault("AUTH__PROVIDER", "hydra")

# Load .env BEFORE importing bindu — `bindu.settings:app_settings = Settings()`
# is constructed at module-import time, so any MTLS__/AUTH__/HYDRA__ vars set
# by a later load_dotenv land in os.environ but never reach the singleton.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agno.agent import Agent  # noqa: E402
from agno.models.openrouter import OpenRouter  # noqa: E402

from bindu.penguin.bindufy import bindufy  # noqa: E402

PORT = int(os.getenv("BINDU_PORT", "5776"))

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
    return agent.run(input=messages).content


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "poet_agent",
    "description": "Writes short poems (max 4 lines). Declines anything else.",
    "deployment": {
        "url": f"https://127.0.0.1:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173", "http://localhost:3775"],
    },
    "capabilities": {"push_notifications": True},
    "global_webhook_url": "http://127.0.0.1:3787/webhooks/bindu/poet_agent",
    "skills": [
        {
            "id": "write_poem",
            "name": "Write a short poem",
            "description": (
                "Compose a short poem (haiku, limerick, free verse, "
                "etc.) on a requested topic and style. Declines "
                "politely for sensitive subjects."
            ),
            "tags": ["poetry", "creative", "writing"],
            "examples": [
                "Write a haiku about autumn",
                "Free verse about loneliness",
            ],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
        }
    ],
}


if __name__ == "__main__":
    bindufy(config, handler)
