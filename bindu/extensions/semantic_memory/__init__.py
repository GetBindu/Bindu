"""Semantic memory extension for Bindu agents.

Provides vector-based knowledge storage and retrieval for agents.
Requires the ``openai`` package as an optional dependency::

    pip install openai

Quick start::

    from bindu.extensions.semantic_memory.memory_store import SemanticMemoryStore
    from bindu.extensions.semantic_memory.embeddings import get_embedding
    from bindu.extensions.semantic_memory.retriever import query_memory

    store = SemanticMemoryStore()
    embedding = get_embedding("Bindu enables the Internet of Agents.")
    store.add("Bindu enables the Internet of Agents.", embedding)

    results = query_memory("What does Bindu do?", store)
"""

from bindu.extensions.semantic_memory.embeddings import get_embedding
from bindu.extensions.semantic_memory.memory_store import MemoryEntry, SemanticMemoryStore
from bindu.extensions.semantic_memory.retriever import cosine_similarity, query_memory

__all__ = [
    "SemanticMemoryStore",
    "MemoryEntry",
    "get_embedding",
    "query_memory",
    "cosine_similarity",
]