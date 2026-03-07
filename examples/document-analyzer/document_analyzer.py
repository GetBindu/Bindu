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

from pypdf import PdfReader
from docx import Document

load_dotenv()

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
def handler(messages):

    if not messages:
        return "No messages received."

    prompt = ""
    extracted_docs = []

    for msg in messages:
        parts = msg.get("parts", [])

        for part in parts:

            if part.get("kind") == "text":
                prompt = part.get("text", "")

            elif part.get("kind") == "file":
                try:
                    b64 = part["file"]["bytes"]
                    file_bytes = base64.b64decode(b64)

                    mime_type = part["file"].get("mimeType", "")

                    doc_text = extract_document_text(file_bytes, mime_type)

                    extracted_docs.append(doc_text)

                except Exception as e:
                    extracted_docs.append(f"Error processing file: {str(e)}")

    if not extracted_docs:
        return "No valid document found in the messages."

    combined_document = "\n\n".join(extracted_docs)

    llm_input = f"""
User Prompt:
{prompt}

Document Content:
{combined_document}

Provide analysis based on the prompt.
"""

    result = agent.run(input=llm_input)

    return result

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
}

if __name__ == "__main__":
    bindufy(config, handler)