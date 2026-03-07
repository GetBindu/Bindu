# Simple in-memory store for semantic memory

MEMORY_STORE = []

def add_memory(text: str, embedding: list[float], agent_id: str):
    MEMORY_STORE.append({
        "text": text,
        "embedding": embedding,
        "agent_id": agent_id
    })


def get_memories():
    return MEMORY_STORE