"""Local Llama 3 Agent via Ollama + Bindu.

Minimal example showing a locally hosted Llama 3 model (Ollama) wrapped
as a Bindu-compatible JSON-RPC agent.

Usage:
    uv run python examples/ollama-llama3-local/llama3_ollama_agent.py

Prerequisites:
    - Ollama running locally
    - `ollama pull llama3`
"""

import os

from agno.agent import Agent
from agno.models.ollama import Ollama
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv


load_dotenv()


agent = Agent(
    instructions=(
        "You are a helpful assistant running locally on Llama 3 via Ollama. "
        "Answer clearly and keep responses concise."
    ),
    model=Ollama(
        id=os.getenv("OLLAMA_MODEL", "llama3"),
        host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    ),
)


config = {
    "author": "your.email@example.com",
    "name": "local_llama3_ollama_agent",
    "description": "Locally hosted Llama 3 agent via Ollama, exposed through Bindu",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": [],
}


def handler(messages: list[dict[str, str]]):
    """Handle Bindu conversation messages with local Ollama model."""
    return agent.run(input=messages)


if __name__ == "__main__":
    bindufy(config, handler)
