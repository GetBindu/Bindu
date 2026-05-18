"""Research Agent — port 5777.

Part of the gateway_test_fleet. Adapted from examples/beginner/
agno_simple_example.py to run on a distinct port with the fleet's
author tag. Uses DuckDuckGo for web search.

Kept close to the original so this agent exercises the SAME code path
a real user would hit — adapting only what's necessary for parallel
operation in the test fleet.

Port: 5xxx range for agents (3xxx is infra). Fleet map: 5773 joke,
5775 math, 5776 poet, 5777 research ← here, 5778 bindu_docs.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 5777)
"""

import os

from dotenv import load_dotenv

# Load .env BEFORE importing bindu — `bindu.settings:app_settings = Settings()`
# is constructed at module-import time, so any MTLS__/AUTH__/HYDRA__ vars set
# by a later load_dotenv land in os.environ but never reach the singleton.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agno.agent import Agent  # noqa: E402
from agno.models.openrouter import OpenRouter  # noqa: E402
from agno.tools.duckduckgo import DuckDuckGoTools  # noqa: E402

from bindu.penguin.bindufy import bindufy  # noqa: E402

PORT = int(os.getenv("BINDU_PORT", "5777"))

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
    return agent.run(input=messages).content


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "research_agent",
    "description": "Researches topics via web search and summarizes findings.",
    "deployment": {
        "url": f"https://127.0.0.1:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173", "http://localhost:3775"],
    },
    "capabilities": {"push_notifications": True},
    "global_webhook_url": "http://127.0.0.1:3787/webhooks/bindu/research_agent",
    "skills": [
        {
            "id": "web_research",
            "name": "Web research",
            "description": (
                "Investigate an open-ended question by searching the "
                "web, synthesize the findings into a structured "
                "Markdown answer with citations. Use for current "
                "events, comparative analysis, or topics outside "
                "general training data."
            ),
            "tags": ["research", "web-search", "synthesis"],
            "examples": [
                "Compare Postgres vs MySQL in 2026",
                "Latest news on x402 protocol adoption",
            ],
            "input_modes": ["text/plain"],
            "output_modes": ["text/markdown"],
        }
    ],
}


if __name__ == "__main__":
    bindufy(config, handler)
