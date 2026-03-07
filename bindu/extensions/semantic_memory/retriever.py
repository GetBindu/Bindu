import math
from .memory_store import get_memories
from .embeddings import get_embedding


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    return dot / (norm_a * norm_b + 1e-8)


def query_memory(query: str, top_k: int = 3):
    query_embedding = get_embedding(query)

    memories = get_memories()

    scored = []
    for m in memories:
        score = cosine_similarity(query_embedding, m["embedding"])
        scored.append((score, m["text"]))

    scored.sort(reverse=True)

    return [text for _, text in scored[:top_k]]