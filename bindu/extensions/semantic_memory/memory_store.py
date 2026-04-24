"""
Simple in-memory semantic memory store.

Allows agents to store text + embeddings and retrieve them later
for cross-agent knowledge sharing experiments.
"""

MEMORY_STORE = []


def add_memory(text: str, embedding: list[float], agent_id: str):
    """Add a memory entry to the store.

    Args:
        text: The memory text content.
        embedding: The embedding vector for the text.
        agent_id: The ID of the agent storing the memory.
    """
    MEMORY_STORE.append(
        {
            "text": text,
            "embedding": embedding,
            "agent_id": agent_id,
        }
    )


def get_memories():
    """Retrieve all stored memories.

    Returns:
        List of memory entries containing text, embedding, and agent_id.
    """
    return MEMORY_STORE
