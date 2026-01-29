from agno.agent import Agent
from agno.models.openai import OpenAIChat


agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    instructions="You are a powerful AI research assistant."
)


def handler(messages: list[dict[str, str]]):
    user_input = messages[-1]["content"]
    result = agent.run(input=user_input)
    return result.to_dict()["content"]


if __name__ == "__main__":
    from bindu.penguin.bindufy import bindufy

    config = {
        "author": "nivas@gmail.com",
        "name": "research_agent",
        "description": "AI Research Assistant that searches, analyzes and summarizes information.",
        "capabilities": {"streaming": True},
        "deployment": {"url": "http://localhost:3778", "protocol_version": "1.0.0"},
        "storage": {"type": "memory"},
        "scheduler": {"type": "memory"},
    }

    bindufy(config=config, handler=handler)
