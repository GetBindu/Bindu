import numpy as np
import os
from openai import OpenAI

# Configure OpenRouter client
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

memory_store = []


def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def cosine_similarity(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))


def store_memory(text: str):
    embedding = get_embedding(text)

    memory_store.append({
        "text": text,
        "embedding": embedding
    })

    print(f"📚 Stored memory: {text[:80]}...")


def retrieve_memory(query: str, top_k: int = 1):

    if not memory_store:
        return []

    query_embedding = get_embedding(query)

    scores = []

    for item in memory_store:
        similarity = cosine_similarity(query_embedding, item["embedding"])

        scores.append({
            "text": item["text"],
            "score": similarity
        })

    scores = sorted(scores, key=lambda x: x["score"], reverse=True)

    # Only return if similarity is strong
    SIMILARITY_THRESHOLD = 0.75
    results = [s for s in scores if s["score"] >= SIMILARITY_THRESHOLD]

    # Prefer most recent stored memory
    results = sorted(
        results,
        key=lambda x: memory_store.index(
            next(item for item in memory_store if item["text"] == x["text"])
        ),
        reverse=True
    )

    return results[:top_k]
