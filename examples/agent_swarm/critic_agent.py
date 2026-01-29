from agno.agent import Agent
from agno.models.openai import OpenAIChat

def build_critic_agent():
    return Agent(
        name="Critic",
        instructions=(
            "You are a critical reviewer. "
            "Check correctness, clarity, completeness, and logic. "
            "Improve the final output and ensure professional quality."
        ),
        model=OpenAIChat(id="gpt-4o-mini"),
    )
