"""Meeting Brief Agent (OpenRouter + Bindu).

Purpose-driven Bindu example that converts raw meeting notes into:
- concise summary
- action items with owners and deadlines
- key risks and follow-ups

Usage:
    uv run python examples/openrouter-meeting-brief/meeting_brief_agent.py
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv


load_dotenv()


agent = Agent(
    instructions=(
        "You are a meeting operations assistant. "
        "Given meeting notes or transcripts, produce:\n"
        "1) an executive summary (3-5 bullet points),\n"
        "2) action items with owner and due date,\n"
        "3) blockers/risks,\n"
        "4) next-step recommendations.\n"
        "If owner or due date is missing, mark it as 'TBD'. "
        "Keep the output structured and practical."
    ),
    model=OpenRouter(
        id=os.getenv("OPENROUTER_MODEL", "openai/gpt-5-mini"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
)


config = {
    "author": "your.email@example.com",
    "name": "openrouter_meeting_brief_agent",
    "description": "Transforms meeting notes into summaries, action items, and next steps",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/meeting-briefing-skill"],
}


def handler(messages: list[dict[str, str]]):
    """Handle Bindu conversation messages with OpenRouter model."""
    return agent.run(input=messages)


if __name__ == "__main__":
    bindufy(config, handler)
