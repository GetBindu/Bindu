import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy

load_dotenv()

# Initialize the Agno Agent
medical_agent = Agent(
    model=OpenRouter(id="google/gemini-2.0-flash-001"),
    instructions=[
        "You are a helpful Medical Assistant.",
        "Provide general health information and wellness advice.",
        "Always include a disclaimer that you are an AI, not a doctor.",
    ],
    markdown=True
)

# Define the Handler (The "Brain" Bindu calls)
def medical_handler(messages: list[dict[str, str]]) -> str:
    """
    Bindu passes a list of messages.
    We pass the latest message to Agno and return the string response.
    """
    user_query = messages[-1]["content"] if messages else ""
    response = medical_agent.run(user_query)
    return response.content

# Define the Bindu Configuration
agent_config = {
    "author": "your-email@example.com", # Required by the source code you found
    "name": "Medical-Chatbot-Agent",
    "description": "A medical guidance agent built with Agno and Bindu",
    "version": "1.0.0",
    "deployment": {
            "url": "http://localhost:3773",
            "expose": True,
            "cors_origins": ["http://localhost:5173"]
        },
}

# Bindufy and Launch
if __name__ == "__main__":
    # This will start the server automatically because run_server=True by default
    bindufy(config=agent_config, handler=medical_handler)
