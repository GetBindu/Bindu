"""Premium Market Insight Advisor with X402 Payment Gating

A Bindu agent that provides premium market insights and financial analysis.
Features X402 payment gating for access to proprietary market analysis.

Features:
- Proprietary deep-chain market analysis
- Investment recommendations and risk assessment
- Developer activity analysis
- X402 payment integration (0.01 USDC per interaction)
- OpenRouter integration with openai/gpt-oss-120b
- Premium insights with payment requirement

Usage:
    python premium_advisor.py

Environment:
    Requires OPENROUTER_API_KEY in .env file
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter


# Initialize the premium market insight agent
agent = Agent(
    instructions="""You are the Oracle of Value, a premium market insight advisor.
    Provide high-value, actionable market insights and investment recommendations.

    Your expertise includes:
    - Deep-chain analysis of blockchain projects
    - Market trend identification and forecasting
    - Risk assessment and safety analysis
    - Developer activity evaluation
    - Investment strategy guidance

    Always provide:
    1. Clear, actionable insights
    2. Risk assessments when relevant
    3. Specific recommendations with reasoning
    4. Market context and timing considerations

    Focus on premium, high-value insights that justify the cost. Be direct,
    confident, and provide specific, actionable advice.""",
    model=OpenRouter(id="openai/gpt-oss-120b", api_key=os.getenv("OPENROUTER_API_KEY")),
)


def handler(messages: list[dict[str, str]]):
    """
    Process incoming messages and return premium market insights.

    This handler is protected by the X402 paywall - users must pay 0.01 USDC
    to access the premium market insights.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Premium market insights and investment recommendations
    """
    # Extract the latest user message
    if messages:
        latest_message = (
            messages[-1].get("content", "")
            if isinstance(messages[-1], dict)
            else str(messages[-1])
        )

        # Run the agent with the latest message
        result = agent.run(input=latest_message)

        # Format the response to be cleaner
        if hasattr(result, "content"):
            return result.content
        elif hasattr(result, "response"):
            return result.response
        else:
            return str(result)

    return "🔮 Welcome to Oracle of Value! Ask me about market insights, investment opportunities, or financial analysis. Premium insights require 0.01 USDC payment."


config = {
    "author": "premium.advisor@example.com",
    "name": "Oracle_of_Value",
    "description": "I provide high-value market insights and investment recommendations. Payment required upfront.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "execution_cost": {
        "amount": "0.01",  # Cost of one interaction
        "token": "USDC",  # Currency
        "network": "base-sepolia",  # Network (Base Testnet)
        "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Dummy ETH Address
    },
    "skills": ["skills/premium-market-insight-skill"],
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "debug_mode": True,
}

# Bindu-fy the agent - converts it to a discoverable, interoperable Bindu agent
bindufy(config, handler)
