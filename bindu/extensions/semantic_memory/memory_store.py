"""
Simple in-memory semantic memory store.

Allows agents to store text + embeddings and retrieve them later
for cross-agent knowledge sharing experiments.
"""


class SemanticMemoryStore:
    """Simple in-memory semantic memory store."""

    def __init__(self) -> None:
        """Initialize an empty memory store."""
        self.memory_store: list[dict] = []

    def add(
        self,
        text: str,
        embedding: list[float],
        agent_id: str = "default",
    ) -> None:
        """Add a memory entry to the store.

        Args:
            text: The memory text content.
            embedding: The embedding vector for the text.
            agent_id: The ID of the agent storing the memory.
        """
        self.memory_store.append(
            {
                "text": text,
                "embedding": embedding,
                "agent_id": agent_id,
            }
        )

    def get_memories(self) -> list[dict]:
        """Retrieve all stored memories.

        Returns:
            List of memory entries containing text, embedding, and agent_id.
        """
        return self.memory_store


MEMORY_STORE = SemanticMemoryStore()


def add_memory(text: str, embedding: list[float], agent_id: str) -> None:
    """Add a memory entry to the default global store."""
    MEMORY_STORE.add(text, embedding, agent_id)


def get_memories() -> list[dict]:
    """Retrieve all memories from the default global store."""
    return MEMORY_STORE.get_memories()
