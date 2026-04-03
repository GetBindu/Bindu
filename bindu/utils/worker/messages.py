"""Message format conversion utilities for worker operations."""

from __future__ import annotations

import base64
import io
from typing import Any, Optional, Union
from uuid import UUID, uuid4

from pypdf import PdfReader
from docx import Document

from bindu.common.protocol.types import Message, Part
from bindu.utils.logging import get_logger

# Import PartConverter from same package
from .parts import PartConverter

logger = get_logger("bindu.utils.worker.messages")

MAX_FILE_SIZE = 10 * 1024 * 1024

# Type aliases for better readability
ChatMessage = dict[str, str]
ProtocolMessage = Message

class FileInterceptor:
    """Native pipeline for intercepting and parsing Base64 file parts."""
    
    SUPPORTED_MIME_TYPES = {
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        """Extract text from a PDF buffer."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join(page.extract_text() for page in reader.pages)
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            return "[Error: Could not parse PDF content]"

    @staticmethod
    def _extract_docx(file_bytes: bytes) -> str:
        """Extract text from a DOCX buffer."""
        try:
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as e:
            logger.error(f"Failed to parse DOCX: {e}")
            return "[Error: Could not parse DOCX content]"

    @staticmethod
    def _decode_plain_text(file_bytes: bytes) -> str:
        """Decode plain text with UTF-8 first and safe fallbacks."""
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                if encoding == "utf-8":
                    return file_bytes.decode(encoding)
                text = file_bytes.decode(encoding)
                logger.info(f"Decoded plain text file using {encoding}")
                return text
            except UnicodeDecodeError:
                continue

        logger.warning("Falling back to replacement decoding for plain text file")
        return file_bytes.decode("utf-8", errors="replace")

    @classmethod
    def intercept_and_parse(cls, parts: list[Part]) -> list[dict[str, Any]]:
        """Intercept file parts, extract text, and replace with text parts."""
        processed_parts = []

        for part in parts:
            if part.get("kind") != "file":
                processed_parts.append(part)
                continue

            file_info = part.get("file") or {}
            mime_type = file_info.get("mimeType", "")
            file_name = file_info.get("name", "uploaded file")
            base64_data = file_info.get("bytes") or file_info.get("data", "")

            if mime_type not in cls.SUPPORTED_MIME_TYPES:
                logger.warning(f"Unsupported MIME type rejected: {mime_type}")
                processed_parts.append(
                    {
                        "kind": "text",
                        "text": (
                            f"[System: User uploaded an unsupported file format "
                            f"({mime_type or 'unknown'}) for {file_name}]"
                        ),
                    }
                )
                continue

            try:
                # Decode the Base64 payload
                if not base64_data:
                    raise ValueError("Missing file bytes")

                file_bytes = base64.b64decode(base64_data)
                if len(file_bytes) > MAX_FILE_SIZE:
                    raise ValueError("File too large")

                extracted_text = ""

                # Route to specific parser based on MIME type
                if mime_type == "application/pdf":
                    extracted_text = cls._extract_pdf(file_bytes)
                elif mime_type == "text/plain":
                    extracted_text = cls._decode_plain_text(file_bytes)
                elif (
                    mime_type
                    == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ):
                    extracted_text = cls._extract_docx(file_bytes)

                # Inject the parsed document as a formatted text prompt
                processed_parts.append(
                    {
                        "kind": "text",
                        "text": (
                            f"--- Document Uploaded: {file_name} ({mime_type}) ---\n"
                            f"{extracted_text}\n"
                            f"--- End of Document ---"
                        ),
                    }
                )

            except Exception as e:
                logger.error(f"Base64 decoding or routing failed: {e}")
                processed_parts.append(
                    {
                        "kind": "text",
                        "text": f"[System: Failed to decode uploaded file data: {e}]",
                    }
                )

        return processed_parts


class MessageConverter:
    """Optimized converter for message format transformations."""

    ROLE_MAP = {"agent": "assistant", "user": "user"}

    @staticmethod
    def to_chat_format(history: list[Message]) -> list[ChatMessage]:
        """Convert protocol messages to standard chat format.

        Now intercepts Base64 files natively and converts them to text parts
        before passing them to the agent framework.
        """
        result = []
        for msg in history:
            original_parts = msg.get("parts", [])
            if not original_parts:
                continue

            # INTERCEPTOR: Parse files into text natively
            processed_parts = FileInterceptor.intercept_and_parse(original_parts)

            role = MessageConverter.ROLE_MAP.get(msg.get("role", "user"), "user")

            # Since all files are now parsed into text, we safely extract it
            content = MessageConverter._extract_text_content(processed_parts)
            if content:
                result.append({"role": role, "content": content})

        return result

    @staticmethod
    def to_protocol_messages(
        result: Any,
        task_id: Optional[Union[str, UUID]] = None,
        context_id: Optional[Union[str, UUID]] = None,
    ) -> list[ProtocolMessage]:
        """Convert manifest result to protocol messages."""
        return [
            Message(
                role="agent",
                parts=PartConverter.result_to_parts(result),
                kind="message",
                message_id=uuid4(),
                task_id=task_id
                if isinstance(task_id, UUID)
                else (UUID(task_id) if task_id else uuid4()),
                context_id=context_id
                if isinstance(context_id, UUID)
                else (UUID(context_id) if context_id else uuid4()),
            )
        ]

    @staticmethod
    def _extract_text_content(parts: list[dict[str, Any]]) -> str:
        """Extract text content from processed parts."""
        if not parts:
            return ""

        text_parts = (
            part["text"]
            for part in parts
            if part.get("kind") == "text" and "text" in part
        )
        return " ".join(text_parts)
