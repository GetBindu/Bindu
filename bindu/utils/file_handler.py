import base64
import io
import logging

logger = logging.getLogger(__name__)

# Strict allowlist to prevent the agent from trying to read binaries/executables
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/csv"
}

def parse_file_part(file_data: dict) -> str:
    """Decodes base64 and extracts text based on MIME type."""
    mime_type = file_data.get("mimeType")
    file_bytes = base64.b64decode(file_data.get("bytes", ""))
    
    try:
        if mime_type in ["text/plain", "text/csv"]:
            return file_bytes.decode("utf-8")
            
        elif mime_type == "application/pdf":
            from pypdf import PdfReader
            pdf = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
            
        else:
            logger.warning(f"Unsupported MIME type passed validation: {mime_type}")
            return ""
            
    except Exception as e:
        logger.error(f"Failed to parse file {file_data.get('name')}: {e}")
        return f"[Error parsing document: {e}]"

def process_agent_messages(messages: list[dict]) -> list[dict]:
    """Validates files, extracts text, and engineers the final prompt for the LLM."""
    if not messages:
        return messages

    last_message = messages[-1]
    user_prompt = ""
    extracted_documents = []
    
    # Iterate through the incoming message parts
    for part in last_message.get("parts", []):
        if part["kind"] == "text":
            user_prompt += part.get("text", "") + "\n"
            
        elif part["kind"] == "file":
            file_data = part["file"]
            mime_type = file_data.get("mimeType")
            file_name = file_data.get("name", "Unknown_Document")
            
            # 1. Validation Check
            if mime_type not in ALLOWED_MIME_TYPES:
                # Instantly reject bad files by returning a system override message
                return [{
                    "role": "assistant", 
                    "content": f"Sorry, I cannot process '{file_name}'. I only support PDF, TXT, and CSV files right now."
                }]
            
            # 2. Extract the text
            parsed_text = parse_file_part(file_data)
            extracted_documents.append(
                f"--- BEGIN DOCUMENT: {file_name} ---\n{parsed_text}\n--- END DOCUMENT ---"
            )

    # 3. Prompt Engineering (Reconstruct the final payload)
    if extracted_documents:
        combined_docs = "\n\n".join(extracted_documents)
        enriched_content = (
            f"You are an expert document analyzer. Read the provided document(s) "
            f"and follow the user's instructions carefully.\n\n"
            f"USER INSTRUCTIONS:\n{user_prompt}\n\n"
            f"DOCUMENTS TO ANALYZE:\n{combined_docs}"
        )
        # Override the original message with the enriched prompt
        messages[-1] = {"role": "user", "content": enriched_content}
    else:
        # Fallback if no files were uploaded, just pass the text normally
        messages[-1] = {"role": "user", "content": user_prompt}

    return messages