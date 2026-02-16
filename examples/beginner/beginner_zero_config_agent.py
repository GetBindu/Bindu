"""Zero-config Bindu agent for question answering and web search.

Purpose: Local agent execution with minimal setup requirements.
Constraints: Requires OPENROUTER_API_KEY environment variable.
Usage: Deploy via bindufy with local HTTP endpoint on port 3773.
"""

import os
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Fail fast if required environment variable is missing
# Zero-config deployment requires explicit API key validation
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY environment variable is required")


# OpenRouter enables model access without local infrastructure
# Local execution via bindufy avoids cloud deployment complexity
agent = Agent(
    instructions="You are a friendly assistant that explains things simply.",
    model=OpenRouter(
        id="openai/gpt-oss-120b",
        api_key=api_key
    ),
    tools=[DuckDuckGoTools()],
)

config = {
    "author": "21uad051@kamarajengg.edu.in",
    "name": "beginner_zero_config_agent",
    "description": "Zero-config local Bindu agent for first-time users",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": ["skills/question-answering", "skills/pdf-processing"],
}

def handler(messages):
    # Return initialization response when no messages provided
    if not messages or len(messages) == 0:
        return [{
            "content": "Bindu agent initialized. Capabilities: question answering, web search via DuckDuckGo.",
            "role": "system"
        }]
    
    # Intent inference: extract text from last user message for skill detection
    last_message = messages[-1] if isinstance(messages, list) else messages
    user_content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
    
    # Skill inference: heuristic phrase-based detection for web-search vs question-answering
    # Web-search detected if message contains explicit search phrases; otherwise defaults to question-answering
    is_web_search = any(term in user_content.lower() for term in ["search", "find", "look up", "what is", "who is", "where is"])
    skill_used = "web-search" if is_web_search else "question-answering"
    
    response = agent.run(input=messages)
    
    return response

# bindufy provides zero-config HTTP deployment without manual server setup
bindufy(config, handler)

# if you want to use tunnel to expose your agent to the internet, use the following command
#bindufy(config, handler, launch=True)
