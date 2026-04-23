---
name: add-example-agent
description: Add a new self-contained example agent under examples/. Use when asked to "create an example for <framework>", "add a tutorial agent", "demo integration with <LLM provider>", or when showcasing a new pattern users should copy.
---

# Add Example Agent

## Overview

Examples under [examples/](../../../examples/) are the fastest way users learn Bindu. Each is a self-contained mini-project demonstrating one integration pattern. Follow existing structure — users and agents discover examples by convention, so inconsistency hurts discoverability.

## Inputs

- `<name>`: kebab-case slug, e.g. `pdf-research-agent`, `weather-research`.
- `<framework>`: Python (agno, langchain, langgraph, crewai) or TypeScript (openai, langchain).
- `<purpose>`: one-sentence "what this demonstrates".

## Safety

- Never commit `.env` files. Only `.env.example` with placeholder values and `# pragma: allowlist secret` to bypass pre-commit.
- Never hardcode API keys, even in comments.
- Never introduce paid-only services without a free-tier alternative. Examples must be runnable by a new user within minutes.
- Never hardcode ports — default to `3773` with `BINDU_PORT` override.

## Execution Contract

1. Pick a matching template from existing examples.
2. Create the directory with the required file set.
3. Wire the handler to `bindufy()` with consistent config.
4. Write a README following the four-section pattern below.
5. Update parent indexes.
6. Test end-to-end in a clean environment before committing.

## Steps

### 1. Pick a template

Find an existing example in the same framework and match its layout:

- Python — simple: [examples/beginner/](../../../examples/beginner/)
- Python — multi-agent: [examples/agent_swarm/](../../../examples/agent_swarm/)
- Python — agno: [examples/medical_agent/](../../../examples/medical_agent/)
- Python — langgraph: [examples/langgraph_blog_writing_agent/](../../../examples/langgraph_blog_writing_agent/)
- TypeScript — openai: [examples/typescript-openai-agent/](../../../examples/typescript-openai-agent/)
- TypeScript — langchain: [examples/typescript-langchain-agent/](../../../examples/typescript-langchain-agent/)

### 2. Create the directory

```
examples/<name>/
├── README.md
├── .env.example
├── main.py          # or index.ts for TypeScript
├── pyproject.toml   # or package.json
└── skills/          # optional, only if agent advertises skills
    └── <skill>/
        └── skill.yaml
```

### 3. Wire the handler

Python handler signature:
```python
def handler(messages: list[dict[str, str]]) -> str | dict:
    ...
```

TypeScript handler signature:
```typescript
async (messages: ChatMessage[]) => Promise<string | HandlerResponse>
```

Call `bindufy(config, handler)` at the bottom of the entry file. Follow the config shape from the template example — don't invent new keys.

### 4. Write README.md

Four sections, in this order:

- **What it does** — one or two sentences.
- **Prerequisites** — API keys, external services. Link docs for each.
- **Setup** — `cp .env.example .env`, fill-in list, install command.
- **Run** — `uv run python main.py` or `npx tsx index.ts`, plus one example curl against `localhost:3773`.

### 5. Update parent indexes

- Add a row to [examples/README.md](../../../examples/README.md).
- If this is a new framework, add it to the main [README.md](../../../README.md) framework table.

### 6. Test in a clean environment

```bash
# Python
cd examples/<name>
uv venv --python 3.12.9
source .venv/bin/activate
uv pip install -e .
python main.py &
sleep 3
curl -X POST http://localhost:3773/ -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"test","params":{"message":{"role":"user","kind":"message","parts":[{"kind":"text","text":"Hello"}],"messageId":"1","contextId":"1","taskId":"1"}}}'
```

If response arrives and the DID signature is present in `metadata`, the example is good.

### 7. Commit

One commit covering the whole example. Conventional commit:

```
feat(examples): add <name> — <one-line purpose>
```

## Never do

- **Never copy-paste secrets** from another example's `.env.example`. Each example lists its own required vars.
- **Never skip the README** — an example without a README is invisible.
- **Never introduce a new pattern** (auth flow, storage backend, deployment target) without matching docs in [docs/](../../../docs/). Examples showcase existing patterns, not unreleased ones.
