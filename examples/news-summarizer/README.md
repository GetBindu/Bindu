# News Summarizer

Local-LLM news research. Agno + Ollama (`llama3.2`) + DuckDuckGo. Hand it a topic, get back the top three headlines, a one-line summary of each, and overall sentiment. Nothing leaves your machine — no OpenRouter call, no API key.

## Setup

```bash
brew install ollama
ollama serve &                  # daemonised; once-per-boot
ollama pull llama3.2            # ~2GB, one-time download
uv sync --extra agents
```

If Ollama isn't running on `http://localhost:11434`, the agent boots fine but the first task fails with `Failed to connect to Ollama`.

## Run

```bash
uv run examples/news-summarizer/news_agent.py
# http://localhost:3773
```

## Talk to it

With `AUTH__ENABLED=false`:

```bash
curl -sS http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"1","params":{"message":{"role":"user","parts":[{"kind":"text","text":"cricket news"}],"kind":"message","messageId":"m1","contextId":"c1","taskId":"t1"}}}'
```

Then `tasks/get` with the same `taskId`. The artifact text is the structured summary (headlines + sentiment). With auth on, sign each body with the agent's DID key — see [`docs/AUTH.md`](../../docs/AUTH.md).
