"""Ollama Local Agent - Run Bindu with Local LLMs (No API Key Required!)

A Bindu agent powered by Ollama for fully local, private AI inference.
No cloud API keys needed - everything runs on your machine.

Features:
- 100% local inference via Ollama
- No API costs or rate limits
- Privacy-first: your data never leaves your machine
- Web search capability via DuckDuckGo
- Full A2A protocol compliance

Prerequisites:
    1. Install Ollama: https://ollama.com/download
    2. Pull a model: ollama pull llama3.2
    3. Start Ollama server: ollama serve

Usage:
    uv run python examples/beginner/ollama_local_agent.py

Test:
    curl http://localhost:3773/.well-known/agent.json

Environment Variables (all optional):
    OLLAMA_MODEL    - Model to use (default: llama3.2)
    OLLAMA_HOST     - Ollama server URL (default: http://localhost:11434)
    BINDU_PORT      - Port to run the agent on (default: 3773)

Closes: https://github.com/GetBindu/Bindu/issues/243
"""

import os

from dotenv import load_dotenv

load_dotenv()

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.ollama import Ollama


# ──────────────────────────────────────────────
# Configuration (override via environment)
# ──────────────────────────────────────────────
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
AGENT_PORT = int(os.getenv("BINDU_PORT", "3773"))


# ──────────────────────────────────────────────
# 1. Define the AI Agent
# ──────────────────────────────────────────────
agent = Agent(
    instructions=(
        "You are a helpful, privacy-focused research assistant running locally via Ollama. "
        "When asked a question, search the web for relevant information and "
        "provide a clear, concise, and well-structured answer. "
        "Always mention that you are running locally for privacy."
    ),
    model=Ollama(id=OLLAMA_MODEL, host=OLLAMA_HOST),
    tools=[DuckDuckGoTools()],
)


# ──────────────────────────────────────────────
# 2. Agent Configuration
# ──────────────────────────────────────────────
config = {
    "author": "contributor@getbindu.com",
    "name": "ollama_local_agent",
    "description": (
        "A privacy-focused research assistant powered by Ollama. "
        "Runs entirely on your local machine with no cloud API calls. "
        "Supports any Ollama-compatible model (Llama 3, Mistral, Phi, etc.)."
    ),
    "version": "1.0.0",
    "deployment": {
        "url": f"http://localhost:{AGENT_PORT}",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "skills": [],
}


# ──────────────────────────────────────────────
# 3. Handler Function
# ──────────────────────────────────────────────
def handler(messages: list[dict[str, str]]):
    """Process incoming messages using the local Ollama model.

    Args:
        messages: List of message dicts with conversation history.

    Returns:
        The agent's response from the local LLM.
    """
    result = agent.run(input=messages)
    return result


# ──────────────────────────────────────────────
# 4. Launch! – Bindu-fy the agent
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n🦙 Starting Ollama Local Agent")
    print(f"   Model: {OLLAMA_MODEL}")
    print(f"   Ollama: {OLLAMA_HOST}")
    print(f"   Port:  {AGENT_PORT}\n")

    bindufy(config, handler)
