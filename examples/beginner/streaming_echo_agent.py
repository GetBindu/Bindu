"""Streaming Echo Agent

A Bindu agent that demonstrates streaming (SSE) responses.
Yields response tokens incrementally, showcasing the message/stream capability.

Features:
- Server-Sent Events (SSE) streaming
- Word-by-word incremental delivery
- Works with both streaming and non-streaming clients
- No external dependencies

Usage:
    python streaming_echo_agent.py

Then test with:
    curl -X POST http://localhost:3773/.well-known/agent.json
    curl -N -X POST http://localhost:3773/a2a \
      -H "Content-Type: application/json" \
      -d '{
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/stream",
        "params": {
          "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello streaming!"}],
            "messageId": "msg-1"
          }
        }
      }'

Environment:
    No environment variables required
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """Handle incoming messages by streaming back the user's latest input word-by-word.

    When the manifest's ``run()`` method returns a generator, Bindu's streaming
    pipeline yields each chunk as an SSE ``artifact`` event, giving clients
    real-time incremental delivery.

    Args:
        messages: List of message dictionaries containing conversation history.

    Yields:
        Individual words from the user's latest message, simulating token-level
        streaming from an LLM.
    """
    user_content = messages[-1]["content"]
    words = user_content.split()

    for i, word in enumerate(words):
        # Add a space between words (but not before the first)
        yield (word if i == 0 else " " + word)


config = {
    "author": "contributor@example.com",
    "name": "streaming_echo_agent",
    "description": "An echo agent that streams responses word-by-word via SSE.",
    "capabilities": {
        "streaming": True,
    },
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/question-answering"],
}

bindufy(config, handler)
