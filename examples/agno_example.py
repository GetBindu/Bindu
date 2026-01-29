"""Example of creating a research assistant agent using Bindu and Agno.

This example demonstrates how to create a simple research assistant agent
that uses DuckDuckGo for web searches and can be deployed as a Bindu agent.

Run with: bindu examples/agno_example.py
Or set environment variables directly and run: python examples/agno_example.py
"""

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
# Note: Infrastructure configs (storage, scheduler, sentry, API keys) are now
# automatically loaded from environment variables. See .env.example for details.
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
    # Storage config loaded from: DATABASE_URL, STORAGE_TYPE
    "auth": {
        "enabled": True,
        "provider": "auth0",
        "domain": "dev-tlzrol0zsxw40ujx.us.auth0.com",
        "audience": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/api/v2/",
        "algorithms": ["RS256"],
        "issuer": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/",
        "jwks_uri": "https://dev-tlzrol0zsxw40ujx.us.auth0.com/.well-known/jwks.json",
        "require_permissions": True,
        "public_endpoints": [
            "/health",
            "/docs",
            "/.well-known/*",
            "/did/resolve*",
            "/agent/skills",
            "/agent/skills/*",
            "/static/*",
            "/api/start-payment-session",
            "/payment-capture*",
            "/api/payment-status/*",
        ],
        "permissions": {
            "message/send": ["agent:write"],
            "tasks/get": ["agent:read"],
            "tasks/cancel": ["agent:write"],
            "tasks/list": ["agent:read"],
            "contexts/list": ["agent:read"],
            "tasks/feedback": ["agent:write"],
        },
    },
    "execution_cost": {
        "amount": "$0.0001",
        "token": "USDC",
        "network": "base-sepolia",
        "pay_to_address": "0x2654bb8B272f117c514aAc3d4032B1795366BA5d",
        "protected_methods": ["message/send"],
    },
    # Negotiation API keys loaded from: OPENROUTER_API_KEY, MEM0_API_KEY, EXA_API_KEY
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
