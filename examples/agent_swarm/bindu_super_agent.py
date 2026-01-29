from bindu.penguin.bindufy import bindufy
from examples.agent_swarm.orchestrator import Orchestrator
from typing import List, Dict, Any


orchestrator = Orchestrator()


def handler(messages: list[dict[str, str]]) -> str:
    """
    Protocol-compliant handler for Bindu.

    Safely extracts user input from message history
    and routes it through the agent swarm.
    """

    # -------- Input Validation --------

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

    # -------- Swarm Execution --------

    try:
        result = orchestrator.run(user_input)
        return result

    except Exception as e:
        return f"Internal agent error: {str(e)}"


if __name__ == "__main__":
    config = {
        "author": "nivasm2823@gmail.com",
        "name": "killer-agent-swarm",
        "description": "Multi-agent AI system for deep research, summarization, critique and reflection.",
        "capabilities": {"streaming": True},
        "deployment": {
            "url": "http://localhost:3780",
            "expose": True,
            "protocol_version": "1.0.0"
        },
        "storage": {"type": "memory"},
        "scheduler": {"type": "memory"}
    }

    bindufy(config=config, handler=handler)
