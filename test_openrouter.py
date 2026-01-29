from agno.agent import Agent
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini")
)

print(agent.run("Say hello in 5 words").content)
