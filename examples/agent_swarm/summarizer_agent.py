from agno.agent import Agent
from agno.models.openai import OpenAIChat

def build_summarizer_agent():
    return Agent(
        name="Summarizer",
        instructions=(
            "You are a professional technical summarizer. "
            "Compress the provided content into a concise, "
            "clear, and high-signal summary. Focus on insights, "
            "not just shortening text."
        ),
        model=OpenAIChat(id="gpt-4o-mini"),
    )
