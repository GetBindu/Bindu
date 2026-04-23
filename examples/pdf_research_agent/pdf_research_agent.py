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

The agent will be live at http://localhost:3775
Send it a message like:
    {"role": "user", "content": "<ALLOWED_BASE_DIR>/paper.pdf"}
or paste raw text directly as the message content.
"""
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv
import os

load_dotenv()

DEFAULT_ALLOWED_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ALLOWED_BASE_DIR = os.path.abspath(
    os.environ.get("ALLOWED_BASE_DIR", DEFAULT_ALLOWED_BASE_DIR)
)
EXAMPLE_PDF_PATH = os.path.join(ALLOWED_BASE_DIR, "paper.pdf")
EXAMPLE_MESSAGE = f'{{"role": "user", "content": "{EXAMPLE_PDF_PATH}"}}'


class DocumentReadError(Exception):
    """Raised when PDF content cannot be read."""

# ---------------------------------------------------------------------------
# 1. Helper — extract text from a PDF path or pass raw text straight through
# ---------------------------------------------------------------------------

def _read_content(source: str) -> str:
    """Return plain text from a PDF file path, or the source string itself."""
    resolved_path = _normalize_pdf_path(source)
    if resolved_path and os.path.isfile(resolved_path):
        try:
            from pypdf import PdfReader  # optional dependency
            reader = PdfReader(resolved_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
            if len(text.strip()) < 100:
                return (
                    f"PDF file '{resolved_path}' appears to be empty or "
                    "contains very little text."
                )
            return text
        except ImportError as exc:
            raise DocumentReadError(
                f"[pypdf not installed — cannot read '{resolved_path}'. "
                "Run: uv add pypdf]"
            ) from exc
        except Exception as e:
            raise DocumentReadError(
                f"Error reading PDF '{resolved_path}': {e!s}"
            ) from e
    return source  # treat as raw document text


def _normalize_pdf_path(source: str) -> str | None:
    """Return a validated absolute PDF path within ALLOWED_BASE_DIR."""
    candidate = source.strip()
    if not candidate.endswith(".pdf"):
        return None

    normalized = os.path.abspath(os.path.realpath(candidate))
    try:
        if os.path.commonpath([normalized, ALLOWED_BASE_DIR]) != ALLOWED_BASE_DIR:
            return None
    except ValueError:
        return None

    return normalized


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
        api_key=os.getenv("OPENROUTER_API_KEY")
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
        "streaming": False
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
                  [{"role": "user", "content": "<ALLOWED_BASE_DIR>/paper.pdf"}]

    Returns:
        Agent response with the document summary.
    """
    try:
        # Grab the most recent user message
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return (
                "No user message found. Please send a PDF path under "
                f"ALLOWED_BASE_DIR ({ALLOWED_BASE_DIR}) or document text. "
                f"Example: {EXAMPLE_MESSAGE}"
            )

        user_input = user_messages[-1].get("content", "").strip()
        if not user_input:
            return (
                "Empty message received. Please provide a PDF path under "
                f"ALLOWED_BASE_DIR ({ALLOWED_BASE_DIR}) or document text. "
                f"Example: {EXAMPLE_MESSAGE}"
            )

        document_text = _read_content(user_input)

        # Limit document size to prevent token overflow
        if len(document_text) > 50000:
            document_text = document_text[:50000] + "\n\n[Document truncated for processing...]"

        # Build a prompt that includes the full document text
        prompt = f"Summarize the following document and highlight the key insights:\n\n{document_text}"
        enriched_messages = [{"role": "user", "content": prompt}]

        result = agent.run(input=enriched_messages)
        if hasattr(result, "content"):
            unwrapped = result.content
        elif hasattr(result, "response"):
            unwrapped = result.response
        else:
            unwrapped = result

        return {"success": True, "data": unwrapped, "error": None}

    except DocumentReadError as e:
        return str(e)
    except Exception as e:
        return f"Error processing request: {str(e)}"


# ---------------------------------------------------------------------------
# 5. Bindu-fy the agent — one call turns it into a live microservice
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🚀 PDF Research Agent running at http://localhost:3773")
    print("📄 Send PDF paths or paste document text to get summaries")
    print(f"🧱 ALLOWED_BASE_DIR: {ALLOWED_BASE_DIR}")
    print(f"🔧 Example: {EXAMPLE_MESSAGE}")
    bindufy(config, handler)
