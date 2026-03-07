"""
Simple demo for the semantic memory extension.

This shows how an agent could store knowledge
and retrieve it using semantic similarity.
"""

from bindu.extensions.semantic_memory.memory_store import add_memory
from bindu.extensions.semantic_memory.embeddings import get_embedding
from bindu.extensions.semantic_memory.retriever import query_memory


def main():
    # Simulate agent storing knowledge
    text = "Bindu enables the Internet of Agents."

    embedding = get_embedding(text)

    add_memory(text, embedding, "research_agent")

    # Query the memory
    results = query_memory("What does Bindu enable?")

    print("\nQuery Results:")
    for r in results:
        print("-", r)


if __name__ == "__main__":
    main()