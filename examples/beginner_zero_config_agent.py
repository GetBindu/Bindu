"""
Beginner Zero-Config Bindu Agent

Purpose:
- Help first-time users run Bindu locally in under 1 minute
- No database, Redis, or cloud dependencies
- Safe default agent for learning Bindu fundamentals
"""

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat
import os

agent = Agent(
    instructions="You are a friendly assistant that explains things simply.",
    model = OpenAIChat(
    id="grok-beta",
    base_url="https://api.x.ai/v1"
)
)

config = {
    "author": "21uad051@kamarajengg.edu.in",
    "name": "beginner_zero_config_agent",
    "description": "Zero-config local Bindu agent for first-time users",
    "deployment": {
        "url": "http://localhost:3774",
        "expose": True,
    },
    "skills": [],
}

def handler(messages):
    return agent.run(input=messages)

bindufy(config, handler)
