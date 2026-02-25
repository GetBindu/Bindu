# Local Llama 3 Agent (Ollama + Bindu)

This example runs a **locally hosted Llama 3 model** via Ollama and exposes it as a **Bindu-compatible JSON-RPC agent**.

## Why this example

- Uses local inference (`ollama`) instead of cloud APIs
- Integrates with Bindu's protocol surface (`message/send`, `tasks/get`)
- Demonstrates structured JSON-RPC requests (not plain text prompts)

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com/) installed and running
- Llama 3 model pulled locally

```bash
ollama pull llama3
```

Optional environment overrides:

```bash
cp examples/ollama-llama3-local/.env.example .env
```

## Run

From repository root:

```bash
uv run python examples/ollama-llama3-local/llama3_ollama_agent.py
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
        "parts": [{"kind": "text", "text": "Explain retrieval-augmented generation in simple terms."}],
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
