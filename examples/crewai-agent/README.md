# CrewAI Research Agent

A two-agent CrewAI crew wrapped with Bindu. Send any topic — a Researcher gathers key facts, a Writer turns them into a clean summary. Served over A2A with a DID identity.

## Prerequisites

- `OPENROUTER_API_KEY` — get one at https://openrouter.ai/keys

## Setup

```bash
cp .env.example .env
# fill in your OPENROUTER_API_KEY
uv sync --extra agents
```

## Run

```bash
uv run examples/crewai-agent/main.py
# http://localhost:3773
```

## Talk to it

```bash
curl -sS http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": "00000000-0000-0000-0000-000000000004",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What is quantum computing?"}],
        "kind": "message",
        "messageId": "00000000-0000-0000-0000-000000000001",
        "contextId": "00000000-0000-0000-0000-000000000002",
        "taskId": "00000000-0000-0000-0000-000000000003"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    }
  }'
```
