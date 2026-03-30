"""Semantic retrieval for Bindu agent memory.

Retrieves the most relevant memories from a SemanticMemoryStore
using cosine similarity between query and stored embeddings.

Example usage::

    from bindu.extensions.semantic_memory.memory_store import SemanticMemoryStore
    from bindu.extensions.semantic_memory.embeddings import get_embedding
    from bindu.extensions.semantic_memory.retriever import query_memory

    store = SemanticMemoryStore()
    embedding = get_embedding("Bindu enables the Internet of Agents.")
    store.add("Bindu enables the Internet of Agents.", embedding)

    results = query_memory("What does Bindu do?", store)
    # results[0].text -> "Bindu enables the Internet of Agents."
"""

from __future__ import annotations

import math
from typing import List

from bindu.extensions.semantic_memory.embeddings import get_embedding
from bindu.extensions.semantic_memory.memory_store import MemoryEntry, SemanticMemoryStore

# Minimum cosine similarity to consider a memory relevant (0.0 – 1.0)
DEFAULT_SIMILARITY_THRESHOLD = 0.75


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First embedding vector.
        b: Second embedding vector.

    Returns:
        Cosine similarity in the range [-1, 1]. Returns 0.0 if either
        vector has zero magnitude.
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    denominator = norm_a * norm_b
    if denominator == 0.0:
        return 0.0
    return dot / denominator


def query_memory(
    query: str,
    store: SemanticMemoryStore,
    top_k: int = 3,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    api_key: str | None = None,
    base_url: str | None = None,
) -> List[MemoryEntry]:
    """Retrieve the most semantically similar memories for a query.

    Args:
        query: The query text to search for.
        store: The SemanticMemoryStore instance to search.
        top_k: Maximum number of results to return.
        threshold: Minimum cosine similarity score (0.0–1.0).
            Memories below this threshold are excluded.
        api_key: Optional API key for embedding generation.
        base_url: Optional base URL for embedding API.

    Returns:
        List of MemoryEntry objects sorted by similarity (highest first),
        limited to ``top_k`` results above ``threshold``.

    Raises:
        ImportError: If the ``openai`` package is not installed.
        ValueError: If no API key is available.
        RuntimeError: If the embedding API call fails.
    """
    entries = store.get_all()
    if not entries:
        return []

    query_embedding = get_embedding(query, api_key=api_key, base_url=base_url)

    scored: List[tuple[float, MemoryEntry]] = []
    for entry in entries:
        score = cosine_similarity(query_embedding, entry.embedding)
        if score >= threshold:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]