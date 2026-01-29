from agno.agent import Agent
from agno.models.openai import OpenAIChat


def build_reflection_agent():
    return Agent(
        instructions="""
You are a reflection and quality evaluation agent.

Analyze the response and return JSON:

{
  "quality": "good" or "bad",
  "issues": ["..."],
  "fix_strategy": "..."
}

Be strict. Ensure factual correctness, clarity, structure, and depth.
""",
        model=OpenAIChat(id="gpt-4o-mini"),
    )
