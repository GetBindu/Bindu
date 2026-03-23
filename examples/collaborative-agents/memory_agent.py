"""Memory agent — stores and retrieves knowledge using semantic similarity."""
from dotenv import load_dotenv
load_dotenv()
import os

from bindu.penguin.bindufy import bindufy
from utils.semantic_memory import retrieve_memory, store_memory


def handler(messages: list[dict]) -> str:
    """Handle store or retrieve memory requests.

    Message format:
        store:<text>    — stores text in memory
        retrieve:<query> — retrieves similar memories
    """
    content = messages[-1]["content"]

    if content.startswith("store:"):
        text = content[len("store:"):].strip()
        store_memory(text)
        return f"Stored in memory: {text[:80]}..."

    elif content.startswith("retrieve:"):
        query = content[len("retrieve:"):].strip()
        results = retrieve_memory(query)
        if results:
            return results[0]["text"]
        return "No relevant memory found."

    return "Unknown command. Use store:<text> or retrieve:<query>."


config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "memory_agent",
    "description": "Stores and retrieves knowledge using semantic similarity.",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3774"),
        "expose": True,
    },
    "skills": [],
}

if __name__ == "__main__":
    bindufy(config, handler)