"""Coordinator agent — orchestrates research and memory agents."""
from dotenv import load_dotenv
load_dotenv()
import os
import time

import httpx
from bindu.penguin.bindufy import bindufy

MEMORY_AGENT_URL = os.getenv("MEMORY_AGENT_URL", "http://localhost:3774")
RESEARCH_AGENT_URL = os.getenv("RESEARCH_AGENT_URL", "http://localhost:3773")

import uuid


def call_agent(url: str, message: str) -> str:
    """Send a message to another Bindu agent, poll until complete, return result."""
    msg_id = str(uuid.uuid4())
    ctx_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    rpc_id = str(uuid.uuid4())

    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
                "kind": "message",
                "messageId": msg_id,
                "contextId": ctx_id,
                "taskId": task_id,
            },
            "configuration": {"acceptedOutputModes": ["application/json"]},
        },
        "id": rpc_id,
    }

    # Send the message
    response = httpx.post(url, json=payload, timeout=30)
    result = response.json()
    actual_task_id = result.get("result", {}).get("id")
    if not actual_task_id:
        return "No response from agent"

    # Poll until completed
    for _ in range(30):
        time.sleep(1)
        poll_payload = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"taskId": actual_task_id},
            "id": str(uuid.uuid4()),
        }
        poll_response = httpx.post(url, json=poll_payload, timeout=10)
        poll_result = poll_response.json().get("result", {})
        state = poll_result.get("status", {}).get("state")

        if state == "completed":
            artifacts = poll_result.get("artifacts", [])
            if artifacts:
                parts = artifacts[0].get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    # Don't return error responses
                    if text and "No response from agent" not in text:
                        return text
            return "No response from agent"

    return "Agent timed out"


def handler(messages: list[dict]) -> str:
    """Coordinate memory and research agents to answer a query."""
    query = messages[-1]["content"]

    # 1. Try memory first
    memory_result = call_agent(MEMORY_AGENT_URL, f"retrieve:{query}")
    if memory_result and memory_result not in (
        "No relevant memory found.",
        "No response from agent",
        "Agent timed out",
    ):
        print("Retrieved from memory.")
        return f"(From Memory) {memory_result}"

    # 2. Fall back to research
    print("Researching...")
    research_result = call_agent(RESEARCH_AGENT_URL, query)

    # 3. Store only valid results
    if research_result and research_result not in (
        "No response from agent",
        "Agent timed out",
    ):
        call_agent(MEMORY_AGENT_URL, f"store:{research_result}")

    return research_result


config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "coordinator_agent",
    "description": (
        "Coordinates research and memory agents to answer questions "
        "about the Bindu framework."
    ),
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3775"),
        "expose": True,
    },
    "skills": [],
}

if __name__ == "__main__":
    bindufy(config, handler)