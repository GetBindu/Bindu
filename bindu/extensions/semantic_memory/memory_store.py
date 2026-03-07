"""
Simple in-memory semantic memory store.

Allows agents to store text + embeddings and retrieve them later
for cross-agent knowledge sharing experiments.
"""

MEMORY_STORE = []

def add_memory(text: str, embedding: list[float], agent_id: str):
    MEMORY_STORE.append({
        "text": text,
        "embedding": embedding,
        "agent_id": agent_id
    })


def get_memories():
    return MEMORY_STORE