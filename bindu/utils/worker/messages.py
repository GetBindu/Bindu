"""Message format conversion utilities for worker operations."""

from __future__ import annotations

from typing import Any, Optional, Union
from uuid import UUID, uuid4

from bindu.common.protocol.types import Message

# Import PartConverter from same package
from .parts import PartConverter

# Type aliases for better readability
ChatMessage = dict[str, str]
ProtocolMessage = Message


class MessageConverter:
    """Optimized converter for message format transformations."""

    # Role mapping for chat format conversion
    ROLE_MAP = {"agent": "assistant", "user": "user"}

    @staticmethod
    def to_chat_format(history: list[Message]) -> list[ChatMessage]:
        """Convert protocol messages to standard chat format.

        Preserves file parts so handlers can process uploaded documents.

        Args:
            history: List of protocol messages

        Returns:
            List of chat messages with role and content fields
        """
        result = []
        for msg in history:
            parts = msg.get("parts", [])
            if not parts:
                continue

            role = MessageConverter.ROLE_MAP.get(msg.get("role", "user"), "user")

            # If message has only text parts, keep original string-content format
            # for backwards compatibility with text-only agents
            has_file = any(p.get("kind") == "file" for p in parts)

            if has_file:
                # Preserve full parts structure so handler can access file bytes
                result.append({"role": role, "parts": parts})
            else:
                content = MessageConverter._extract_text_content(msg)
                if content:
                    result.append({"role": role, "content": content})

        return result

    @staticmethod
    def to_protocol_messages(
        result: Any,
        task_id: Optional[Union[str, UUID]] = None,
        context_id: Optional[Union[str, UUID]] = None,
    ) -> list[ProtocolMessage]:
        """Convert manifest result to protocol messages.

        Args:
            result: Manifest execution result
            task_id: Optional task ID
            context_id: Optional context ID

        Returns:
            List of protocol messages
        """
        # Message TypedDict requires task_id and context_id as Required fields
        # Use placeholder UUIDs if not provided
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
    def _extract_text_content(message: Message) -> str:
        """Extract text content from protocol message."""
        parts = message.get("parts", [])
        if not parts:
            return ""

        # Use generator for memory efficiency
        text_parts = (
            part["text"]
            for part in parts
            if part.get("kind") == "text" and "text" in part
        )
        return " ".join(text_parts)
