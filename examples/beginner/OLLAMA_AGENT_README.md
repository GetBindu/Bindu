# 🦙 Ollama Local Agent

A Bindu agent powered by [Ollama](https://ollama.com) for fully local, private AI inference.
**No cloud API keys needed** — everything runs on your machine.

> Closes [#243](https://github.com/GetBindu/Bindu/issues/243)

## Features

- 🔒 **100% Local** — Your data never leaves your machine
- 💸 **Zero Cost** — No API keys or usage fees
- 🌐 **Web Search** — DuckDuckGo integration for real-time info
- 🤖 **Any Model** — Works with Llama 3, Mistral, Phi, Gemma, and more
- ✅ **A2A Compliant** — Full Bindu protocol support

## Prerequisites

1. **Install Ollama**: https://ollama.com/download
2. **Pull a model**:
   ```bash
   ollama pull llama3.2
   ```
3. **Ollama is running** (starts automatically on install, or run `ollama serve`)

## Quick Start

```bash
# From the Bindu repo root
uv sync --dev
uv run python examples/beginner/ollama_local_agent.py
```

Your agent is now live at `http://localhost:3773` 🎉

## Configuration

All configuration is via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2` | Ollama model to use |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `BINDU_PORT` | `3773` | Port for the Bindu agent |

### Example with custom model

```bash
OLLAMA_MODEL=mistral BINDU_PORT=3774 uv run python examples/beginner/ollama_local_agent.py
```

## Testing

### Check Agent Card
```bash
curl http://localhost:3773/.well-known/agent.json
```

### Send a Message
```python
import json, urllib.request

payload = {
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "What is Bindu?"}],
            "kind": "message",
            "messageId": "test-001",
            "contextId": "ctx-001",
            "taskId": "task-001",
        },
        "configuration": {"acceptedOutputModes": ["application/json"]},
    },
    "id": "req-001",
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    "http://localhost:3773/",
    data=data,
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req)
print(json.loads(resp.read()))
```

## Supported Models

Any model available in Ollama works. Popular choices:

| Model | Pull Command | Best For |
|-------|-------------|----------|
| Llama 3.2 | `ollama pull llama3.2` | General purpose |
| Mistral | `ollama pull mistral` | Fast responses |
| Phi-3 | `ollama pull phi3` | Lightweight |
| Gemma 2 | `ollama pull gemma2` | Balanced |
| CodeLlama | `ollama pull codellama` | Code tasks |
