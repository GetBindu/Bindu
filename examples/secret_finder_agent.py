import os 
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Our list of dangerous words
SECRET_KEYWORDS = ["password", "secret" , "api_key", "token", "private_key", "credentials"]

# The actuall "tool" agent will use
def scan_text_from_secrets(text_content: str) -> dict:
    """Scans the provided text for comman secret keywords"""
    found_secrets = []
    text_lower = text_content.lower()

    for word in SECRET_KEYWORDS:
        if word in text_lower:
            found_secrets.append(word)
    
    # Return a dictonary (JSON format) that Bindu understands
    return {
        "is_safe": len(found_secrets) == 0,
        "found_words": found_secrets,
        "warning": "🚨 SECRET DETECTED..!" if found_secrets else "Text look clean and safe"
    }


# Create the Agent Brain
agent = Agent(
    name="secret_finder",
    description="I am a security agent that scans for any accidentally leaked secrets.",
    instructions=[
        "You are a dedicated security auditing agent.",
        "Use the scan_text_from_secrets tool when a user provides text.",
        "Report the findings clearly, listing any detected secrets."
    ],
    # Tell the AI it's allowed to use your new tool function!
    tools=[scan_text_from_secrets],
)

# Bindu Configuration: Linking our Python Agent to the YAML Menu
config = {
    "author": "your.email@example.com",
    "name": "secret_finder_agent",
    "description": "An agent that scans for leaked secrets.",
    "deployment": {
        "url": "http://localhost:3774",
        "expose": True
    },
    # This matches the folder name from earlier!
    "skills": ["examples/skills/secret-finder"]
}

# The Bridge that processes incoming messages
def handler(messages: list[dict]):
    """Process incoming Bindu messages."""
    return agent.run(input=messages)

if __name__ == "__main__":
    print("🚀 Starting Secret Finder Agent...")
    print("📍 Skill advertised: Secret Finder (secret-finder-v1)")
    # Launch it!
    bindufy(config, handler)
