"""Semantic memory store for Bindu agents.

Provides a class-based in-memory store for text and embeddings.
Each instance maintains its own isolated memory — safe for use
across multiple async workers without shared global state.

Example usage::

    store = SemanticMemoryStore()
    store.add("Bindu enables the Internet of Agents.", embedding)
    memories = store.get_all()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class MemoryEntry:
    """A single memory entry with text and its vector embedding."""

    text: str
    embedding: List[float]
    agent_id: str = ""


class SemanticMemoryStore:
    """Thread-safe in-memory store for agent knowledge.

    Uses instance-level storage instead of a global list, making it
    safe for use in async web workers where a shared global MEMORY_STORE
    would be visible across all requests and agents.

    For production use with persistence across restarts or workers,
    replace this with a vector database backend (e.g. pgvector, Qdrant).
    """

    def __init__(self) -> None:
        """Initialize an empty memory store."""
        self._entries: List[MemoryEntry] = []

    def add(self, text: str, embedding: List[float], agent_id: str = "") -> None:
        """Store a text entry with its embedding.

        Args:
            text: The text content to store.
            embedding: Vector embedding of the text.
            agent_id: Optional identifier of the agent storing this memory.
        """
        self._entries.append(MemoryEntry(text=text, embedding=embedding, agent_id=agent_id))

    def get_all(self) -> List[MemoryEntry]:
        """Return all stored memory entries.

        Returns:
            List of all MemoryEntry objects in insertion order.
        """
        return list(self._entries)

    def clear(self) -> None:
        """Remove all stored entries."""
        self._entries.clear()

    def __len__(self) -> int:
        """Return the number of stored entries."""
        return len(self._entries)