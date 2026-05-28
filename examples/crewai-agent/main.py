import os

from crewai import Agent, Crew, LLM, Task
from dotenv import load_dotenv

from bindu.penguin.bindufy import bindufy

load_dotenv()

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    raise RuntimeError("OPENROUTER_API_KEY environment variable is required")

llm = LLM(
    model="openrouter/openai/gpt-4o-mini",
    api_key=openrouter_api_key,
)

researcher = Agent(
    role="Researcher",
    goal="Research the given topic and gather key facts and insights.",
    backstory="You are an expert researcher who finds accurate, concise information on any topic.",
    llm=llm,
    verbose=False,
)

writer = Agent(
    role="Writer",
    goal="Write a clear and engaging summary based on the research provided.",
    backstory="You are a skilled writer who turns raw research into readable, well-structured summaries.",
    llm=llm,
    verbose=False,
)


def handler(messages):
    if not messages:
        return "No messages received. Please provide a topic to research."

    last = messages[-1]
    query = last.get("content", "") if isinstance(last, dict) else str(last)

    if not query.strip():
        return "Please provide a topic to research."

    research_task = Task(
        description=f"Research this topic thoroughly: {query}",
        expected_output="A list of key facts, insights, and important points about the topic.",
        agent=researcher,
    )

    write_task = Task(
        description="Using the research provided, write a clear 3-5 paragraph summary.",
        expected_output="A well-structured, readable summary of the topic.",
        agent=writer,
    )

    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)


config = {
    "author": "your.email@example.com",
    "name": "crewai_research_agent",
    "description": "A two-agent CrewAI crew that researches any topic and writes a clear summary.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["*"],
    },
    "skills": ["skills/crewai-research"],
    "auth": {"enabled": False},
}

if __name__ == "__main__":
    bindufy(config, handler)
