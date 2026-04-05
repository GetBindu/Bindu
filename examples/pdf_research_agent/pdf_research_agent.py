"""
PDF Research Agent Example for Bindu

This example agent accepts either a PDF file path or raw text and
returns a structured summary. It demonstrates how to wrap a simple
document-processing workflow using `bindufy()` so the agent becomes
a live service.

Prerequisites
-------------
    uv add bindu agno pypdf python-dotenv

Usage
-----
    export OPENROUTER_API_KEY="your_api_key_here"  # pragma: allowlist secret
    python pdf_research_agent.py

The agent will be live at http://localhost:3773
Send it a message like:
    {"role": "user", "content": "/path/to/paper.pdf"}
or paste raw text directly as the message content.
"""

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError(
        "Missing OPENROUTER_API_KEY for OpenRouter model construction in pdf_research_agent.py"
    )

ALLOWED_BASE_DIR = Path(__file__).parent.resolve()


class DocumentReadError(ValueError):
    """Raised when a document source cannot be read safely."""


# ---------------------------------------------------------------------------
# 1. Helper — extract text from a PDF path or pass raw text straight through
# ---------------------------------------------------------------------------


def _read_content(source: str) -> str:
    """Return plain text from a PDF file path, or the source string itself."""
    source_text = source.strip()
    if source_text.endswith(".pdf"):
        resolved_path = Path(os.path.realpath(os.path.expanduser(source_text)))

        try:
            common = Path(
                os.path.commonpath([str(ALLOWED_BASE_DIR), str(resolved_path)])
            )
        except ValueError as exc:
            raise DocumentReadError(
                "PDF path is outside the allowed document directory"
            ) from exc

        if common != ALLOWED_BASE_DIR:
            raise DocumentReadError(
                "PDF path is outside the allowed document directory"
            )
        if not resolved_path.is_file():
            raise DocumentReadError(f"PDF file does not exist: {resolved_path}")

        try:
            from pypdf import PdfReader  # optional dependency

            reader = PdfReader(str(resolved_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
            if len(text.strip()) < 100:
                raise DocumentReadError(
                    f"PDF file '{resolved_path}' appears to be empty or contains very little text."
                )
            return text
        except ImportError:
            raise DocumentReadError(
                f"pypdf not installed and cannot read '{resolved_path}'. Run: uv add pypdf"
            )
        except Exception as e:
            if isinstance(e, DocumentReadError):
                raise
            raise DocumentReadError(
                f"Error reading PDF '{resolved_path}': {str(e)}"
            ) from e
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
        "Be factual and brief. If the text is too short or unclear, say so."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=OPENROUTER_API_KEY,
    ),
    markdown=True,  # Enable markdown formatting for better output
)


# ---------------------------------------------------------------------------
# 3. Bindu configuration
# ---------------------------------------------------------------------------

config = {
    "author": "your.email@example.com",
    "name": "pdf_research_agent",
    "description": "Summarises PDF files and document text using OpenRouter.",
    "version": "1.0.0",
    "capabilities": {
        "file_processing": ["pdf"],
        "text_analysis": ["summarization", "research"],
        "streaming": False,
    },
    "skills": ["skills/pdf-research-skill"],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
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
    try:
        # Grab the most recent user message
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return {
                "success": False,
                "data": None,
                "error": "No user message found. Please send a PDF path or document text.",
            }

        user_input = user_messages[-1].get("content", "").strip()
        if not user_input:
            return {
                "success": False,
                "data": None,
                "error": "Empty message received. Please provide a PDF path or document text.",
            }

        try:
            document_text = _read_content(user_input)
        except DocumentReadError as exc:
            return {"success": False, "data": None, "error": str(exc)}

        # Limit document size to prevent token overflow
        if len(document_text) > 50000:
            document_text = (
                document_text[:50000] + "\n\n[Document truncated for processing...]"
            )

        # Build a prompt that includes the full document text
        prompt = f"Summarize the following document and highlight the key insights:\n\n{document_text}"
        enriched_messages = [{"role": "user", "content": prompt}]

        result = agent.run(input=enriched_messages)
        return {"success": True, "data": result, "error": None}

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Error processing request: {e}",
        }


# ---------------------------------------------------------------------------
# 5. Bindu-fy the agent — one call turns it into a live microservice
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🚀 PDF Research Agent running at http://localhost:3773")
    print("📄 Send PDF paths or paste document text to get summaries")
    print('🔧 Example: {"role": "user", "content": "/path/to/paper.pdf"}')
    bindufy(config, handler)
