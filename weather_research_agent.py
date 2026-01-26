

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat


# Initialize the weather research agent
agent = Agent(
    instructions="You are a weather research assistant. Find current weather information and forecasts for cities around the world. Use search tools to get real-time weather data and provide accurate forecasts.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Agent configuration for Bindu
config = {
    "author": "bindu.builder@getbindu.com",
    "name": "weather_research_agent",
    "description": "Research agent that finds current weather and forecasts for any city worldwide",
    "deployment": {"url": "http://localhost:3773", "expose": True}
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
    result = agent.run(input=messages)
    return result

# Bindu-fy the agent - converts it to a discoverable, interoperable Bindu agent
bindufy(config, handler)