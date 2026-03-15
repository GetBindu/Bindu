"""
PDF Research Agent Example for Bindu

This example agent accepts either a PDF file path or raw text and
returns a structured summary. It demonstrates how to wrap a simple
document-processing workflow using `bindufy()` so the agent becomes
a live service.


Prerequisites
-------------
    uv add bindu agno openai pypdf

Usage
-----
    export OPENAI_API_KEY="sk-..."
    python pdf_research_agent.py

The agent will be live at http://localhost:3775
Send it a message like:
    {"role": "user", "content": "/path/to/paper.pdf"}
or paste raw text directly as the message content.
"""

import os

from agno.agent import Agent
from agno.models.ollama import Ollama

from bindu.penguin.bindufy import bindufy

# ---------------------------------------------------------------------------
# 1. Helper — extract text from a PDF path or pass raw text straight through
# ---------------------------------------------------------------------------

def _read_content(source: str) -> str:
    """Return plain text from a PDF file path, or the source string itself."""
    if source.strip().endswith(".pdf") and os.path.isfile(source.strip()):
        try:
            from pypdf import PdfReader  # optional dependency
            reader = PdfReader(source.strip())
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except ImportError:
            return (
                f"[pypdf not installed — cannot read '{source.strip()}'. "
                "Run: uv add pypdf]"
            )
    return source  # treat as raw document text


# ---------------------------------------------------------------------------
# 2. Agent definition
# ---------------------------------------------------------------------------

agent = Agent(
    instructions=(
        "You are a research assistant that reads documents and produces clear, "
        "concise summaries. When given document text:\n"
        "  1. Identify the main topic or thesis.\n"
        "  2. List the key findings or arguments (3-5 bullet points).\n"
        "  3. Note any important conclusions or recommendations.\n"
        "Be factual and brief.  If the text is too short or unclear, say so."
    ),
    model=Ollama(id="llama3"),
)


# ---------------------------------------------------------------------------
# 3. Bindu configuration
# ---------------------------------------------------------------------------

config = {
    "author": "your.email@example.com",
    "name": "pdf_research_agent",
    "description": "Summarises PDF files and document text using an LLM.",
    "version": "1.0.0",
    "capabilities": {},
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": "http://localhost:3775",
        "expose": True,
    },
}


# ---------------------------------------------------------------------------
# 4. Handler — the bridge between Bindu messages and the agent
# ---------------------------------------------------------------------------

def handler(messages: list[dict[str, str]]):
    """
    Receive a conversation history from Bindu, extract the latest user
    message, read its content (PDF or raw text), and return a summary.

    Args:
        messages: Standard A2A message list, e.g.
                  [{"role": "user", "content": "/path/to/doc.pdf"}]

    Returns:
        Agent response with the document summary.
    """
    # Grab the most recent user message
    user_messages = [m for m in messages if m.get("role") == "user"]
    if not user_messages:
        return "No user message found. Please send a PDF path or document text."

    user_input = user_messages[-1].get("content", "")
    document_text = _read_content(user_input)

    # Build a prompt that includes the full document text
    prompt = f"Summarize the following document and highlight the key insights:\n\n{document_text}"
    enriched_messages = [{"role": "user", "content": prompt}]

    result = agent.run(input=enriched_messages)
    return result


# ---------------------------------------------------------------------------
# 5. Bindu-fy the agent — one call turns it into a live microservice
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("PDF Research Agent running at http://localhost:3775")
    bindufy(config, handler)