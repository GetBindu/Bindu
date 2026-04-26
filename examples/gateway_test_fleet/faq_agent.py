"""FAQ Agent — port 3778.

Part of the gateway_test_fleet. Adapted from examples/beginner/
faq_agent.py. Answers questions about the Bindu documentation using
web search, formatted as Markdown with citations.

Environment:
    OPENROUTER_API_KEY — required (examples/.env)
    BINDU_PORT         — optional override (default 3778)
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

PORT = int(os.getenv("BINDU_PORT", "3778"))

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
    return agent.run(input=messages)


config = {
    "author": "gateway_test_fleet@getbindu.com",
    "name": "bindu_docs_agent",
    "description": "Answers Bindu documentation questions with cited sources.",
    "deployment": {
        "url": f"http://localhost:{PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": [],
}


if __name__ == "__main__":
    bindufy(config, handler)
