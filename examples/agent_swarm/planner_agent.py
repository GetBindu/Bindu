from agno.agent import Agent
from agno.models.openai import OpenAIChat


def build_planner_agent():
    return Agent(
        instructions="""
You are a master AI task planner.

Given a user query, produce a JSON execution plan for an AI agent swarm.

You must output ONLY valid JSON.

Available agents:
- researcher
- summarizer
- critic

Rules:
1. Always include at least research → summary → critique
2. Output format:

{
  "steps": [
      {"agent": "researcher", "task": "..."},
      {"agent": "summarizer", "task": "..."},
      {"agent": "critic", "task": "..."}
  ]
}
""",
        model=OpenAIChat(id="gpt-4o-mini"),
    )
