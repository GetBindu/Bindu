"""Translator Agent — Bindu Collab Pipeline

A Bindu-powered agent that accepts text and translates it into a target
language (default: Spanish). This is Agent 2 in the collaboration pipeline,
designed to receive summarized text from Agent 1 via the orchestrator.

Features:
- Translates text while preserving structure and meaning
- Zero-config: uses in-memory storage and scheduler
- Runs on port 3774 to coexist with the Summarizer Agent (port 3773)

Usage:
    python translator_agent.py

Environment:
    Requires OPENROUTER_API_KEY or OPENAI_API_KEY in .env file
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# LLM-backed translation agent
# ---------------------------------------------------------------------------
translator = Agent(
    instructions=(
        "You are a professional translator. Translate the given text into Spanish. "
        "Preserve the original formatting (bullet points, structure, etc.). "
        "Return ONLY the translated text with no explanations or commentary."
    ),
    model=OpenRouter(
        id="openai/gpt-4.1-nano",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
)


# ---------------------------------------------------------------------------
# Bindu handler
# ---------------------------------------------------------------------------
def handler(messages: list[dict[str, str]]):
    """Process messages and return the translated version of the user's input.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        The agent's translated response.
    """
    return translator.run(input=messages)


# ---------------------------------------------------------------------------
# Agent configuration — runs on port 3774 (separate from Summarizer)
# ---------------------------------------------------------------------------
config = {
    "author": "collab-pipeline@example.com",
    "name": "translator_agent",
    "description": "Translates text into Spanish. Part of the Collab Pipeline example.",
    "deployment": {
        "url": "http://localhost:3774",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/question-answering", "skills/translation"],
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
}

# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    bindufy(config, handler)
