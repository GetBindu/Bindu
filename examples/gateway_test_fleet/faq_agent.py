"""FAQ Agent — port 5778.

Part of the gateway_test_fleet. Adapted from examples/beginner/
faq_agent.py. Answers questions about the Bindu documentation using
web search, formatted as Markdown with citations.

Port: 5xxx range for agents (3xxx is infra). Fleet map: 5773 joke,
5775 math, 5776 poet, 5777 research, 5778 bindu_docs ← here.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 5778)
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
from agno.tools.duckduckgo import DuckDuckGoTools  # noqa: E402

from bindu.penguin.bindufy import bindufy  # noqa: E402

PORT = int(os.getenv("BINDU_PORT", "5778"))

agent = Agent(
    name="Bindu Docs Agent",
    instructions=(
        "You are an expert assistant for the Bindu framework. Search "
        "the Bindu documentation (docs.getbindu.com) to answer the "
        "user's question.\n\n"
        "Formatting rules:\n"
        "- Return your answer in CLEAN Markdown.\n"
        "- Use '##' for main headers and bullet points for lists.\n"
        "- Do NOT wrap the whole response in a JSON code block.\n"
        "- End with a '### Sources' section listing the links you used."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
    tools=[DuckDuckGoTools()],
    markdown=True,
)


def handler(messages: list[dict[str, str]]):
    """Run the Docs Q&A agent against the conversation history."""
    return agent.run(input=messages).content


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "bindu_docs_agent",
    "description": "Answers Bindu documentation questions with cited sources.",
    "deployment": {
        "url": f"https://127.0.0.1:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173", "http://localhost:3775"],
    },
    "capabilities": {"push_notifications": True},
    "global_webhook_url": "http://127.0.0.1:3787/webhooks/bindu/bindu_docs_agent",
    "skills": [
        {
            "id": "bindu_docs_qa",
            "name": "Bindu docs Q&A",
            "description": (
                "Answer questions about the Bindu framework, A2A "
                "protocol, agent lifecycle, DIDs, x402 payments, and "
                "related topics by searching docs.getbindu.com. Returns "
                "Markdown with a Sources section."
            ),
            "tags": ["docs", "bindu", "qa", "framework"],
            "examples": [
                "What is Bindu?",
                "How does the task lifecycle work?",
                "Explain reference_task_ids",
            ],
            "input_modes": ["text/plain"],
            "output_modes": ["text/markdown"],
        }
    ],
}


if __name__ == "__main__":
    bindufy(config, handler)
