import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from bindu.penguin.bindufy import bindufy
from bindu.dspy.prompt_router import route_prompt
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    instructions="You are a movie research assistant. You help users find information about movies, actors, directors, and related topics. You can search the web for the latest information and provide concise summaries.", 
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "ast@gmail.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}

# Handler function
async def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    agent.instructions = await route_prompt(initial_prompt=agent.instructions)
    print(f"Updated agent instructions: {agent.instructions}")
    result = agent.run(input=messages)
    return result

# Bindu-fy it
bindufy(config, handler)

# Use tunnel to expose your agent to the internet
# bindufy(config, handler, launch=True)