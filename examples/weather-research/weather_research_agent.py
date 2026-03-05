"""Weather Research Agent with Web Search

A Bindu agent that provides weather information using DuckDuckGo web search.
Provides current weather conditions and forecasts for any location worldwide.

Features:
- Web search via DuckDuckGo for real-time weather data
- Weather research and forecasting capabilities
- OpenRouter integration with openai/gpt-oss-120b
- Clean, synthesized responses without raw search results

Usage:
    python weather_research_agent.py

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


# Initialize the weather research agent
agent = Agent(
    instructions="You are a weather research assistant. When asked about weather, provide a clear, concise weather report with current conditions, temperature, and forecast. Focus on the most relevant information and present it in an organized, easy-to-read format. Avoid showing multiple search results - synthesize the information into a single coherent response.",
    model=OpenRouter(id="openai/gpt-oss-120b", api_key=os.getenv("OPENROUTER_API_KEY")),
    tools=[DuckDuckGoTools()],
)

# Agent configuration for Bindu
config = {
    "author": "bindu.builder@getbindu.com",
    "name": "weather_research_agent",
    "description": "Research agent that finds current weather and forecasts for any city worldwide",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/weather-research-skill"],
}


# Message handler function
def handler(messages: list[dict[str, str]]):
    """
    Process incoming messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response with weather information
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

    return "Please provide a location for weather information."


# Bindu-fy the agent - converts it to a discoverable, interoperable Bindu agent
bindufy(config, handler)
