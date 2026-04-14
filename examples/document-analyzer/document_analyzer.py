"""
Document Analyzer Agent — analyzes uploaded PDF/DOCX documents based on a user prompt.

Features:
- Works with Bindu A2A FilePart messages
- Supports PDF and DOCX
- Prompt-driven analysis
- Multi-file support
"""

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv

import os
import io
import base64
from typing import Any

from pypdf import PdfReader
from docx import Document
from bindu.utils.logging import get_logger

logger = get_logger("examples.document_analyzer")

load_dotenv()

# Define LLM agent
agent = Agent(
    instructions="""
You are an advanced document analysis assistant.

Your job is to analyze uploaded documents and answer the user's prompt
based ONLY on the document content.

Guidelines:
- Carefully read the document text
- Extract relevant insights requested in the prompt
- Be structured and clear
- If the prompt asks for research insights, provide:
  - methodology
  - research gap
  - key findings
  - conclusions
- If the prompt asks for summary, provide concise bullet points
- Do not hallucinate information outside the document
""",
    model=OpenRouter(
        id="arcee-ai/trinity-large-preview:free",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    ),
)


# Document Parsing
def extract_text_from_pdf(file_bytes):
    """Extract text from pdf bytes"""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {str(e)}")
    text = []

    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        except Exception:
            continue

    return "\n".join(text)


def extract_text_from_docx(file_bytes):
    """Extract text from docx bytes"""
    try:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        logger.error(f"Error extracting DOCX text: {e}")
        return ""


def extract_document_text(file_bytes, mime_type):
    """Parse document according to their mime type"""
    if mime_type == "application/pdf":
        return extract_text_from_pdf(file_bytes)

    if mime_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        return extract_text_from_docx(file_bytes)

    raise ValueError(f"Unsupported file type: {mime_type}")


# FilePart processing
def get_file_bytes(part):
    """Extract file bytes from FilePart"""
    file_info = part["file"]

    if "bytes" in file_info:
        data = file_info["bytes"]
    elif "data" in file_info:
        data = file_info["data"]
    else:
        raise ValueError("Unsupported file part format")

    if isinstance(data, str):
        import base64

        return base64.b64decode(data)

    return data


# Handler
def _collect_prompt_and_documents(
    messages: list[dict[str, Any]],
) -> tuple[str, list[str], list[str]]:
    """Support both raw A2A messages and runtime chat-format messages."""
    prompt_parts: list[str] = []
    extracted_docs: list[str] = []
    errors: list[str] = []

    for msg in messages:
        role = msg.get("role")
        if role is not None and role != "user":
            continue

        # Runtime path: manifest worker passes chat-format messages.
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            prompt_parts.append(content)

        # Compatibility path: raw A2A messages with parts.
        parts = msg.get("parts") or []
        for part in parts:
            if part.get("kind") == "text":
                text = part.get("text", "")
                if text:
                    prompt_parts.append(text)
            elif part.get("kind") == "file":
                try:
                    file_info = part.get("file", {})
                    b64_data = file_info.get("bytes") or file_info.get("data")
                    mime_type = file_info.get("mimeType", "")

                    if not b64_data:
                        raise ValueError("No file data found")

                    file_bytes = (
                        base64.b64decode(b64_data)
                        if isinstance(b64_data, str)
                        else b64_data
                    )
                    doc_text = extract_document_text(file_bytes, mime_type)
                    extracted_docs.append(doc_text)
                except Exception as e:
                    errors.append(str(e))

    return "\n".join(prompt_parts).strip(), extracted_docs, errors


def handler(messages: list[dict]):
    """
    Receives task.history — a list of A2A Message objects.
    Each message has: role, parts[], kind, messageId, contextId, taskId
    Each part has: kind="text"|"file", and either text or file.bytes+mimeType
    """
    if not messages:
        return "No messages received."
    prompt, extracted_docs, errors = _collect_prompt_and_documents(messages)

    if not extracted_docs:
        if errors:
            return "Failed to process documents:\n" + "\n".join(errors)
        return "No valid document found in the messages."

    combined_document = "\n\n".join(extracted_docs)
    result = agent.run(
        input=f"""
User Prompt:
{prompt}

Document Content:
{combined_document}

Provide analysis based on the prompt.
"""
    )
    return result


# Bindu config
config = {
    "author": "vyomrohila@gmail.com",
    "name": "document_analyzer_agent",
    "description": "AI agent that analyzes uploaded PDF or DOCX documents based on a user prompt.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/document-processing"],
    "enable_system_message": False,
}

if __name__ == "__main__":
    bindufy(config, handler)
