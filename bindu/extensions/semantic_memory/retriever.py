"""Semantic memory retrieval helpers."""

import math

from .embeddings import get_embedding
from .memory_store import SemanticMemoryStore, get_memories


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    return dot / (norm_a * norm_b + 1e-8)


def query_memory(
    query: str,
    store: SemanticMemoryStore | None = None,
    top_k: int = 3,
    threshold: float = 0.0,
) -> list[str]:
    """Query semantic memory and retrieve top-k similar memories.

    Args:
        query: Query text to search for.
        store: Optional memory store instance. Uses global store if omitted.
        top_k: Maximum number of results to return.
        threshold: Minimum similarity score to include.

    Returns:
        List of memory texts ranked by similarity.
    """
    query_embedding = get_embedding(query)

    memories = store.get_memories() if store is not None else get_memories()

    scored: list[tuple[float, str]] = []
    for memory in memories:
        score = cosine_similarity(query_embedding, memory["embedding"])
        if score >= threshold:
            scored.append((score, memory["text"]))

    scored.sort(reverse=True)

    return [text for _, text in scored[:top_k]]
