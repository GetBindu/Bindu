# PDF Research

Hand it a PDF (path on the host, or base64 `file` part) and ask a question — the agent extracts the text with `pypdf` and answers off the content. Agno + OpenRouter (`openai/gpt-oss-120b`).

## Setup

```bash
export OPENROUTER_API_KEY=<get one at https://openrouter.ai/keys>
uv sync --extra agents
```

## Run

```bash
uv run examples/pdf_research_agent/pdf_research_agent.py
# http://localhost:3773
```

## Talk to it

With `AUTH__ENABLED=false`, no document attached:

```bash
curl -sS http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"1","params":{"message":{"role":"user","parts":[{"kind":"text","text":"What is this about?"}],"kind":"message","messageId":"m1","contextId":"c1","taskId":"t1"}}}'
# → asks you to provide the document text or file path
```

Two ways to attach:
- **By path** in the prompt: `"Summarise /absolute/path/to/paper.pdf"` — agent reads the file off the host.
- **As a `file` part** with base64 bytes alongside the `text` part. See [`docs/FILE_HANDLING_&_UPLOADS.md`](../../docs/FILE_HANDLING_&_UPLOADS.md).

With auth on, sign each body with the agent's DID key — see [`docs/AUTH.md`](../../docs/AUTH.md).
