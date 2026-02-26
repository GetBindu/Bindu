# Meeting Brief Agent (OpenRouter + Bindu)

This example uses **OpenRouter** and exposes a focused, Bindu-compatible JSON-RPC agent that turns meeting notes into practical outputs.

## Why this example

- Uses `OPENROUTER_API_KEY`
- Produces useful structured output (summary, actions, risks, next steps)
- Uses Bindu JSON-RPC methods (`message/send`, `tasks/get`)

## Prerequisites

- Python 3.12+
- OpenRouter API key

Create env file:

```bash
cp examples/openrouter-meeting-brief/.env.example .env
```

## Run

From repository root:

```bash
uv run python examples/openrouter-meeting-brief/meeting_brief_agent.py
```

The agent starts at `http://localhost:3773`.

## Test with JSON-RPC

Send a structured Bindu request:

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Meeting notes: Priya will finalize dashboard copy by Friday. Arjun needs API latency data before QA sign-off. Release target is next Wednesday. Risk: staging instability."}],
        "kind": "message",
        "messageId": "msg-001",
        "contextId": "ctx-001",
        "taskId": "task-001"
      },
      "configuration": {
        "acceptedOutputModes": ["application/json"]
      }
    },
    "id": "1"
  }'
```

Then fetch the task result:

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {"taskId": "task-001"},
    "id": "2"
  }'
```
