import os
import uvicorn
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# 1. Define the Agno Agent
agent = Agent(
    name="DataExtractor",
    instructions="You are an expert at extracting structured data from unstructured text, web scrapes, and documents.",
    model=OpenAIChat(id="gpt-4o"),
)

# 2. Use Bindu's Native Configuration for Negotiation
config = {
    "name": "data_extraction_negotiator",
    "description": "Agent for web scraping and data extraction tasks.",
    "skills": ["skills/data-extraction"],  # Points to the skill.yaml file we created
    "negotiation": {
        # Bindu natively uses embeddings to match tasks to skills automatically
        "embedding_api_key": os.getenv("OPENAI_API_KEY", "dummy-key-for-local-testing"),
    }
}

# 3. Let Bindu create the app and automatically handle the /agent/negotiation endpoint!
app = bindufy(agent, config=config)

if __name__ == "__main__":
    print("Starting Native Bindu Agent on port 3773...")
    uvicorn.run(app, host="0.0.0.0", port=3773)