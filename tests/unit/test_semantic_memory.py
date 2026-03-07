from bindu.extensions.semantic_memory.memory_store import add_memory
from bindu.extensions.semantic_memory.retriever import query_memory

def test_memory_store():
    add_memory("Bindu powers the Internet of Agents.", [0.1]*1536, "agent_a")
    results = query_memory("What powers agents?")
    assert len(results) > 0