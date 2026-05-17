# Hermes Agent

Nous Research's [hermes-agent](https://github.com/NousResearch/hermes-agent) bindufied. A real tool-using coding/research agent (web, file, code-exec) with tiered safety controls — pick `read` (web only), `sandbox` (web + file + moa), or `full` (everything) via env.

PEP-723-style script header: `uv run` reads the dependency comment at the top of `hermes_simple_example.py` and resolves `bindu` + the `hermes-agent` git dep on first run.

## Setup

```bash
export OPENROUTER_API_KEY=<get one at https://openrouter.ai/keys>
# Optional: pick a tier (default: read)
export HERMES_TOOL_TIER=sandbox   # read | sandbox | full
```

No `uv sync` needed — the script header installs deps on demand.

## Run

```bash
uv run examples/hermes_agent/hermes_simple_example.py
# http://localhost:3773
```

## Talk to it

There's a working signed-request reference client in this folder:

```bash
uv run examples/hermes_agent/call.py "summarize bindu in one sentence"
```

`call.py` reuses the agent's own Ed25519 key (`.bindu/private.pem`) as the caller identity, fetches an OAuth token from Hydra, signs each JSON-RPC body, and polls `tasks/get` until terminal. Read it as the canonical reference for the auth-on flow.

Without auth, the same plain curl as every other example works:

```bash
curl -sS http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"1","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Summarize bindu in one sentence."}],"kind":"message","messageId":"m1","contextId":"c1","taskId":"t1"}}}'
```

## Heads-up

The example may break against newer `hermes-agent` releases — current `AIAgent.__init__` doesn't accept the `persist_session` kwarg this example passes. If you see `unexpected keyword argument 'persist_session'`, drop that arg from the `AIAgent(...)` call or pin an older `hermes-agent` SHA in the script header.

See [`docs/AUTH.md`](../../docs/AUTH.md) for the auth-on flow.
