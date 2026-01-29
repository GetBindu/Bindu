from agno.agent import Agent
from agno.models.openai import OpenAIChat

def build_research_agent():
    return Agent(
        name="Researcher",
        instructions=(
            "You are a deep research agent. "
            "Explore the topic thoroughly, identify key facts, "
            "important insights, recent trends, and technical depth. "
            "Return a structured, detailed research output."
        ),
        model=OpenAIChat(id="gpt-4o-mini"),
    )
