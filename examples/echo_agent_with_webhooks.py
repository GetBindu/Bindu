"""Echo agent with push notification support.

This example demonstrates how to configure push notifications when using bindufy.
The agent will send webhook notifications for all task state changes and artifacts.
"""

import os
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Load environment variables from .env file
load_dotenv()

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)


# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    "negotiation": {
        "embedding_api_key": os.getenv("OPENROUTER_API_KEY"),  # Load from environment
    },
    # Enable push notifications capability
    "capabilities": {"push_notifications": True},
    # Optional: Configure global webhook for all tasks
    # If not specified, clients must provide webhook in each request
    "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
    "global_webhook_token": "secret_abc123",
}


# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=messages)
    return result


# Bindu-fy it
bindufy(config, handler)
