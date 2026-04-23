"""
Document Analyzer Agent — analyzes uploaded PDF/DOCX documents based on a user prompt.

Features:
- Works with Bindu A2A FilePart messages
- Supports PDF and DOCX
- Prompt-driven analysis
- Multi-file support
"""

from bindu.penguin.bindufy import bindufy
from bindu.utils.logging import get_logger
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv

import os
import io
import base64

from pypdf import PdfReader
from docx import Document

load_dotenv()

logger = get_logger("examples.document_analyzer")

# Define LLM agent
agent = Agent(
    instructions = """
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
    model = OpenRouter(
        id = "arcee-ai/trinity-large-preview:free",
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
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs])

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
def handler(messages: list[dict]):
    """
    Receives task.history — a list of A2A Message objects.
    Each message has: role, parts[], kind, messageId, contextId, taskId
    Each part has: kind="text"|"file", and either text or file.bytes+mimeType
    """
    if not messages:
        return "No messages received."
    import json
    print("DEBUG messages:", json.dumps(messages, indent=2, default=str))

    prompt = ""
    extracted_docs = []
    errors = []

    for msg in messages:
        # if a role is provided, only process user messages; treat missing
        # roles as coming from the user so that tests/clients without a role
        # field still work.
        role = msg.get("role")
        if role is not None and role != "user":
            continue

        # be defensive: parts could be None or omitted
        parts = msg.get("parts") or []
        for part in parts:
            if part.get("kind") == "text":
                prompt = part.get("text", "")

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
                    if not doc_text or not doc_text.strip():
                        file_ref = (
                            file_info.get("name")
                            or file_info.get("filename")
                            or file_info.get("path")
                            or "unknown"
                        )
                        error_reason = "Empty or whitespace-only extracted content"
                        logger.warning(
                            "Skipping extracted document because parsed content is empty",
                            file=file_ref,
                            mime_type=mime_type,
                            reason="empty_or_whitespace_content",
                        )
                        errors.append(f"{file_ref}: {error_reason}")
                        continue
                    extracted_docs.append(doc_text)

                except Exception as e:
                    file_ref = (
                        file_info.get("name")
                        or file_info.get("filename")
                        or file_info.get("path")
                        or "unknown"
                    )
                    logger.error(
                        "Failed to process uploaded file",
                        file=file_ref,
                        mime_type=file_info.get("mimeType", ""),
                        reason=str(e),
                    )
                    errors.append(f"{file_ref}: {str(e)}")

    if errors and not extracted_docs:
        return "Failed to process uploaded files:\n" + "\n".join(errors)

    if not extracted_docs:
        return "No valid document found in the messages."

    combined_document = "\n\n".join(extracted_docs)
    result = agent.run(input=f"""
User Prompt:
{prompt}

Document Content:
{combined_document}

Provide analysis based on the prompt.
""")
    result_content = result.content

    if errors:
        return (
            f"{result_content}\n\n"
            "Warning: Some files could not be processed:\n"
            f"{'\n'.join(errors)}"
        )

    return result_content


# Bindu config
config = {
    "author" : "vyomrohila@gmail.com",
    "name" : "document_analyzer_agent",
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
