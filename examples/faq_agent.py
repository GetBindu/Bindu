"""
FAQ Agent Example for Bindu 🌻

This example demonstrates how to build a simple FAQ-style agent
using Bindu. The agent responds to common questions about Bindu
and helps new users understand how agent handlers work.

How to run:
    python examples/faq_agent.py

After starting, open:
    http://localhost:3773/docs
"""

from bindu.penguin.bindufy import bindufy

# ---------------------------------------------------------------------------
# Predefined FAQ data
# ---------------------------------------------------------------------------
# This dictionary maps common user questions (in lowercase)
# to their corresponding answers.
#
# Keeping FAQs in a simple dictionary makes this example:
# - Easy to read
# - Easy to extend
# - Beginner-friendly
FAQ_DATA = {
    "what is bindu": "Bindu is an identity, communication, and payments layer for AI agents.",
    "what protocols does bindu support": "Bindu supports A2A, AP2, and X402 protocols.",
    "is bindu open source": "Yes, Bindu is fully open source under the Apache 2.0 license.",
    "how do agents communicate": "Agents communicate using open protocols and task-based workflows.",
}

# ---------------------------------------------------------------------------
# Agent handler
# ---------------------------------------------------------------------------
# This function is called by Bindu whenever the agent receives a message.
# It receives the full conversation history as a list of messages.
def handler(messages):
    """
    Handle incoming messages and return an appropriate FAQ response.

    Args:
        messages: List of message dictionaries representing the conversation history.

    Returns:
        A string response answering the user's question.
    """

    # Extract the latest user message and normalize it
    user_input = messages[-1]["content"].lower()

    # Check if the user's message matches any known FAQ question
    for question, answer in FAQ_DATA.items():
        if question in user_input:
            return answer

    # Fallback response when no FAQ match is found
    return (
        "I don't have an answer for that yet.\n\n"
        "Try asking:\n"
        "- What is Bindu?\n"
        "- What protocols does Bindu support?\n"
        "- Is Bindu open source?"
    )

# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------
# This configuration defines how the agent appears and runs in Bindu.
config = {
    # Author email used for agent identity and registration
    "author": "anushasingh0501@gmail.com",

    # Human-readable agent name
    "name": "faq_agent",

    # Short description shown in agent metadata
    "description": "A simple FAQ agent for answering common questions",

    # Local deployment configuration
    "deployment": {"url": "http://localhost:3773", "expose": True},

    # Skills are descriptive metadata that help with agent discovery
    "skills": ["skills/question-answering"]
,
}

# ---------------------------------------------------------------------------
# Bindufy the agent
# ---------------------------------------------------------------------------
# This call transforms the handler and configuration into
# a fully networked, discoverable Bindu agent and starts the server.
bindufy(config, handler)
