import pytest
from bindu.extensions.semantic_memory.memory_store import SemanticMemoryStore
from bindu.extensions.semantic_memory.retriever import query_memory


@pytest.fixture(autouse=True)
def clean_store():
    """Provide a fresh store for each test."""
    store = SemanticMemoryStore()
    return store


def test_memory_store(clean_store):
    clean_store.add("Bindu powers the Internet of Agents.", [0.1] * 1536)
    results = query_memory("What powers agents?", clean_store, threshold=0.0)
    assert len(results) > 0
