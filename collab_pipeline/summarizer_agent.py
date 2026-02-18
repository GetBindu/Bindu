"""Summarizer Agent — Bindu Collab Pipeline

A Bindu-powered agent that accepts text and returns a concise summary.
This is Agent 1 in the collaboration pipeline, designed to work with
the Translator Agent (Agent 2) via A2A protocol.

Features:
- Summarizes long text into key points
- Zero-config: uses in-memory storage and scheduler
- Framework-agnostic handler compatible with any LLM backend

Usage:
    python summarizer_agent.py

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
# LLM-backed summarization agent
# ---------------------------------------------------------------------------
summarizer = Agent(
    instructions=(
        "You are a concise summarizer. When given text, extract the key points "
        "and return a clear, well-structured summary in 3-5 bullet points. "
        "Keep the summary under 150 words. Do NOT add commentary or opinions."
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
    """Process messages and return a summarized version of the user's input.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        The agent's summary response.
    """
    return summarizer.run(input=messages)


# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------
config = {
    "author": "collab-pipeline@example.com",
    "name": "summarizer_agent",
    "description": "Summarizes text into concise bullet points. Part of the Collab Pipeline example.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/question-answering", "skills/summarization"],
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
}

# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    bindufy(config, handler)
