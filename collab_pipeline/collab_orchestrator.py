"""Collab Orchestrator — A2A Protocol Client

Demonstrates inter-agent communication via the A2A (Agent-to-Agent) protocol.
This orchestrator connects two Bindu agents in a pipeline:

    User Input → Summarizer Agent (port 3773) → Translator Agent (port 3774)

The full flow is:
1. Send text to the Summarizer Agent via A2A `message/send`
2. Poll for task completion via `tasks/get`
3. Extract the summary from completed task artifacts
4. Send the summary to the Translator Agent via A2A `message/send`
5. Poll for task completion
6. Print the full pipeline output

Usage:
    1. Start both agents first (see README.md)
    2. python collab_orchestrator.py

Requirements:
    pip install httpx
"""

import asyncio
import sys
import time
import uuid

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SUMMARIZER_URL = "http://localhost:3773"
TRANSLATOR_URL = "http://localhost:3774"

POLL_INTERVAL = 1.0   # seconds between task polls
POLL_TIMEOUT = 60.0   # max seconds to wait for a task to complete

SAMPLE_TEXT = """\
Artificial intelligence (AI) has rapidly evolved from a niche academic pursuit
into a transformative force reshaping industries worldwide. In healthcare,
AI-powered diagnostic tools are achieving accuracy rates comparable to
experienced physicians, particularly in radiology and pathology. The financial
sector leverages machine learning algorithms for fraud detection, algorithmic
trading, and personalized banking experiences. Meanwhile, natural language
processing breakthroughs have enabled conversational AI systems that can draft
legal documents, write code, and even compose music. However, these advances
come with significant ethical considerations, including concerns about job
displacement, algorithmic bias, and the environmental cost of training large
models. Experts emphasize that responsible AI development requires transparent
governance frameworks, diverse development teams, and ongoing public discourse
about the societal implications of increasingly autonomous systems.
"""


# ---------------------------------------------------------------------------
# A2A Protocol Helpers
# ---------------------------------------------------------------------------
def build_message_send_request(text: str, context_id: str | None = None) -> dict:
    """Build a JSON-RPC 2.0 request for A2A `message/send`.

    Args:
        text: The text content to send to the agent.
        context_id: Optional conversation context ID. Generated if not provided.

    Returns:
        A valid A2A JSON-RPC request dictionary.
    """
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "message_id": str(uuid.uuid4()),
                "context_id": context_id or str(uuid.uuid4()),
            }
        },
    }


def build_task_get_request(task_id: str) -> dict:
    """Build a JSON-RPC 2.0 request for A2A `tasks/get`.

    Args:
        task_id: The ID of the task to check.

    Returns:
        A valid A2A JSON-RPC request dictionary.
    """
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/get",
        "params": {"task_id": task_id},
    }


def extract_text_from_artifacts(task: dict) -> str:
    """Extract text content from task artifacts.

    Args:
        task: A completed task dictionary from the A2A response.

    Returns:
        Concatenated text from all text-kind artifact parts.
    """
    texts = []
    for artifact in task.get("artifacts", []):
        for part in artifact.get("parts", []):
            if part.get("kind") == "text":
                texts.append(part["text"])
    return "\n".join(texts) if texts else ""


# ---------------------------------------------------------------------------
# A2A Communication
# ---------------------------------------------------------------------------
async def send_message(client: httpx.AsyncClient, agent_url: str, text: str) -> str:
    """Send a message to a Bindu agent and wait for the completed task.

    Args:
        client: An httpx AsyncClient instance.
        agent_url: Base URL of the Bindu agent (e.g. http://localhost:3773).
        text: Text content to send.

    Returns:
        The text extracted from the completed task's artifacts.

    Raises:
        TimeoutError: If the task does not complete within POLL_TIMEOUT.
        RuntimeError: If the task fails or the response is unexpected.
    """
    # Step 1: Send message
    request = build_message_send_request(text)
    response = await client.post(agent_url, json=request, timeout=30.0)
    response.raise_for_status()
    result = response.json()

    if "error" in result:
        raise RuntimeError(f"A2A error: {result['error']}")

    task = result.get("result", {})
    task_id = task.get("id")
    state = task.get("status", {}).get("state", "unknown")

    print(f"  📨 Task submitted: {task_id} (state={state})")

    # Step 2: Poll for completion
    start_time = time.time()
    while state not in ("completed", "failed", "canceled"):
        if time.time() - start_time > POLL_TIMEOUT:
            raise TimeoutError(f"Task {task_id} did not complete within {POLL_TIMEOUT}s")

        await asyncio.sleep(POLL_INTERVAL)

        poll_request = build_task_get_request(task_id)
        poll_response = await client.post(agent_url, json=poll_request, timeout=15.0)
        poll_response.raise_for_status()
        poll_result = poll_response.json()

        if "error" in poll_result:
            raise RuntimeError(f"A2A poll error: {poll_result['error']}")

        task = poll_result.get("result", {})
        state = task.get("status", {}).get("state", "unknown")
        print(f"  ⏳ Polling... state={state}")

    if state == "failed":
        raise RuntimeError(f"Task {task_id} failed")
    if state == "canceled":
        raise RuntimeError(f"Task {task_id} was canceled")

    # Step 3: Extract result
    output = extract_text_from_artifacts(task)
    if not output:
        # Fallback: check history messages
        for msg in reversed(task.get("history", [])):
            if msg.get("role") == "agent":
                for part in msg.get("parts", []):
                    if part.get("kind") == "text":
                        output = part["text"]
                        break
                if output:
                    break

    return output


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
async def run_pipeline(text: str) -> None:
    """Execute the full Summarize → Translate pipeline.

    Args:
        text: The original text to process.
    """
    print("=" * 70)
    print("🚀 Bindu Collab Pipeline — Summarize → Translate")
    print("=" * 70)

    print(f"\n📄 Original Text ({len(text.split())} words):")
    print("-" * 50)
    print(text.strip())

    async with httpx.AsyncClient() as client:
        # ----- Stage 1: Summarize -----
        print("\n" + "=" * 70)
        print("📝 Stage 1: Sending to Summarizer Agent (port 3773)")
        print("=" * 70)
        try:
            summary = await send_message(client, SUMMARIZER_URL, text)
        except Exception as e:
            print(f"\n❌ Summarizer Agent error: {e}")
            print("   Make sure summarizer_agent.py is running on port 3773")
            return

        print(f"\n✅ Summary received:")
        print("-" * 50)
        print(summary)

        # ----- Stage 2: Translate -----
        print("\n" + "=" * 70)
        print("🌍 Stage 2: Sending to Translator Agent (port 3774)")
        print("=" * 70)
        try:
            translation = await send_message(client, TRANSLATOR_URL, summary)
        except Exception as e:
            print(f"\n❌ Translator Agent error: {e}")
            print("   Make sure translator_agent.py is running on port 3774")
            return

        print(f"\n✅ Translation received:")
        print("-" * 50)
        print(translation)

        # ----- Final Output -----
        print("\n" + "=" * 70)
        print("🎉 Pipeline Complete!")
        print("=" * 70)
        print(f"\n📄 Original:    {len(text.split())} words")
        print(f"📝 Summary:     {len(summary.split())} words")
        print(f"🌍 Translation: {len(translation.split())} words")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Allow custom text via command line argument
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    else:
        input_text = SAMPLE_TEXT

    asyncio.run(run_pipeline(input_text))
