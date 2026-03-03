"""
Bindu Super Agent — NightSky Swarm entry point.

Merges agno-based orchestrator with LangGraph Scout → Analyst → Publisher pipeline.
Deployed as a Bindu microservice with Redis scheduler.
"""

from bindu.penguin.bindufy import bindufy
from examples.agent_swarm.orchestrator import Orchestrator
from dotenv import load_dotenv
import os

load_dotenv(override=True)

orchestrator = Orchestrator()


def handler(messages: list[dict[str, str]]) -> str:
    """
    Protocol-compliant handler for Bindu.
    Validates input and routes through the full swarm pipeline:
    agno (Planner → Researcher → Summarizer → Critic → Reflection)
    → LangGraph (Scout → Analyst → Publisher)
    """

    # ── Input Validation ──────────────────────────────────────
    if not isinstance(messages, list):
        return "Invalid input format: messages must be a list."

    if not messages:
        return "No input message received."

    last_msg = messages[-1]

    if not isinstance(last_msg, dict):
        return "Invalid message structure."

    user_input = last_msg.get("content")

    if not user_input or not isinstance(user_input, str):
        return "Empty or invalid message content."

    # ── Swarm Execution ───────────────────────────────────────
    try:
        result = orchestrator.run(user_input)
        return result
    except Exception as e:
        return f"Internal agent error: {str(e)}"


if __name__ == "__main__":
    config = {
        "author": "nivasm2823@gmail.com",
        "name": "killer-agent-swarm",
        "description": (
            "NightSky Swarm — agno orchestrator merged with LangGraph pipeline. "
            "Deep research, summarization, critique, reflection, "
            "Scout web research, structured analysis, and markdown report generation."
        ),
        "capabilities": {"streaming": False},
        "deployment": {
            "url": "http://localhost:3780",
            "expose": True,
            "protocol_version": "1.0.0",
        },
        "storage": {"type": "memory"},
        "scheduler": {
            "type": "redis",
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        },
    }

    bindufy(config=config, handler=handler)