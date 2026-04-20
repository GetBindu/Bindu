"""Medical Research Agent with Web Search

A Bindu agent that provides medical information and health guidance using DuckDuckGo web search.
Provides general health information, symptom analysis, and wellness recommendations.

Features:
- Web search via DuckDuckGo for real-time medical information
- Medical research and symptom analysis capabilities
- OpenRouter integration with google/gemini-2.0-flash-001
- Clean, synthesized responses with medical disclaimers
- Health and wellness guidance

Usage:
    python medical_agent.py

Environment:
    Requires OPENROUTER_API_KEY in .env file
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openrouter import OpenRouter


# Initialize the medical research agent
agent = Agent(
    instructions="""You are a medical research assistant. When asked about health or medical topics, provide clear, accurate information with appropriate disclaimers. 

Key guidelines:
- Always include a medical disclaimer stating this is not professional medical advice
- Provide general health information and educational content
- For specific medical concerns, recommend consulting healthcare professionals
- Use web search to find current, reliable medical information
- Present information in an organized, easy-to-read format
- Avoid making definitive diagnoses or treatment recommendations
- Focus on evidence-based information from reputable sources

Response format:
- Start with relevant medical information
- Include supporting details and context
- End with a clear medical disclaimer
- Avoid showing multiple search results - synthesize information coherently""",
    model=OpenRouter(
        id="google/gemini-2.0-flash-001",
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
    tools=[DuckDuckGoTools()],
    markdown=True
)

# Agent configuration for Bindu
config = {
    "author": "bindu.builder@getbindu.com",
    "name": "medical_agent",
    "description": "Medical research agent that provides health information, symptom analysis, and wellness guidance",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": ["skills/medical-research-skill"],
}

# Message handler function
def handler(messages: list[dict[str, str]]):
    """
    Process incoming messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response with medical information and appropriate disclaimers
    """
    # Extract the latest user message
    if messages:
        latest_message = messages[-1].get('content', '') if isinstance(messages[-1], dict) else str(messages[-1])

        # Run the agent with the latest message
        result = agent.run(input=latest_message)

        # Format the response to be cleaner
        if hasattr(result, 'content'):
            return result.content
        elif hasattr(result, 'response'):
            return result.response
        else:
            return str(result)

    return "Please provide a health or medical question. Remember, I provide general information for educational purposes only."

# Bindu-fy the agent - converts it to a discoverable, interoperable Bindu agent
bindufy(config, handler)
