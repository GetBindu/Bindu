# Hermes Agent via Bindu

Run [Nous Research's hermes-agent](https://github.com/NousResearch/hermes-agent) — a
tool-using coding and research agent with web, filesystem, and code-execution
tools — as a Bindu A2A microservice.

One file, two dependencies, self-contained.

What you get the moment it boots:

- DID (decentralized) identity — every artifact is Ed25519-signed
- A2A JSON-RPC endpoint on `http://localhost:3773`
- OAuth2-ready auth hooks
- x402 (USDC) payment support
- Optional public FRP tunnel via `deployment.expose`

---

## Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)
- An API key for whichever model you pick — `OPENROUTER_API_KEY` by default
  (the script defaults to `anthropic/claude-3.5-haiku` via OpenRouter)

---

## Quick start

Hermes-agent is not on PyPI yet, so we install it straight from GitHub.

### Option A — one command, throw-away environment

`uv` reads the PEP 723 header in `hermes_simple_example.py` and builds an
isolated env on the fly:

```bash
cp .env.example .env
$EDITOR .env                       # set OPENROUTER_API_KEY

uv run hermes_simple_example.py
```

### Option B — persistent install

```bash
uv pip install bindu \
  "hermes-agent @ git+https://github.com/NousResearch/hermes-agent.git"

cp .env.example .env
$EDITOR .env                       # set OPENROUTER_API_KEY

python hermes_simple_example.py
```

On startup the banner prints the agent's DID and the local A2A endpoint
(`http://localhost:3773` by default).

---

## Configuration

All settings are environment variables. Copy `.env.example` to `.env` and edit.

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Model provider key (required for default model) |
| `HERMES_MODEL` | `anthropic/claude-3.5-haiku` | Any model the provider routes |
| `HERMES_TIER` | `read` | Toolset tier — see below |
| `HERMES_URL` | `http://localhost:3773` | Public URL Bindu advertises |
| `HERMES_NAME` | `hermes` | Agent display name |
| `HERMES_AUTHOR` | `you@example.com` | Author field on the agent card |

You can swap `OPENROUTER_API_KEY` for `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
depending on what `HERMES_MODEL` routes to.

---

## Safety tiers

`HERMES_TIER` gates which Hermes toolsets the agent can call. Hermes ships
~20 toolsets — including terminal access and arbitrary code execution — so
pick the tier that matches where the agent is reachable:

| `HERMES_TIER` | Toolsets exposed | When to use |
|---|---|---|
| `read` *(default)* | `web` (search + extract) | Public / tunneled deployments |
| `sandbox` | `web` + `file` + `moa` | Trusted caller, local filesystem OK |
| `full` | Everything — terminal, browser, code exec, MCP | **Localhost only** |

> ⚠️ **Never combine `full` with a public tunnel (`deployment.expose: true`).**
> That's remote code execution as a service.

---

## Calling the agent

The endpoint speaks standard A2A JSON-RPC — see the authoritative
[openapi.yaml](https://github.com/GetBindu/Bindu/blob/main/openapi.yaml).
IDs must be real UUIDs; `tasks/get` keys off `taskId`, not `id`.

```bash
uuid() { uuidgen | tr 'A-Z' 'a-z'; }
RID=$(uuid); MID=$(uuid); CID=$(uuid); TID=$(uuid)

# 1. Fire — returns immediately with state: submitted + taskId
curl -s -X POST http://localhost:3773/ \
  -H 'Content-Type: application/json' \
  -d "{
    \"jsonrpc\":\"2.0\",\"method\":\"message/send\",\"id\":\"$RID\",
    \"params\":{
      \"message\":{
        \"role\":\"user\",
        \"parts\":[{\"kind\":\"text\",\"text\":\"summarize bindu in one sentence\"}],
        \"kind\":\"message\",
        \"messageId\":\"$MID\",\"contextId\":\"$CID\",\"taskId\":\"$TID\"
      },
      \"configuration\":{\"acceptedOutputModes\":[\"application/json\"]}
    }
  }" | jq

# 2. Pull — loop until state is completed / failed / input-required
curl -s -X POST http://localhost:3773/ \
  -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tasks/get\",\"id\":\"$(uuid)\",\"params\":{\"taskId\":\"$TID\"}}" \
  | jq '.result | {state: .status.state, text: .artifacts[0].parts[0].text}'
```

Other JSON-RPC methods available on the same endpoint:

- `tasks/list` — list tasks in a context
- `tasks/cancel` — cancel a running task
- `contexts/list` — list conversation contexts
- `tasks/pushNotificationConfig/set` — webhook callbacks
- `message/stream` — SSE streaming

---

## How it fits together

```
curl ─► Bindu HTTP (:3773) ─► ManifestWorker ─► handler(messages)
                                                    │
                                                    ▼
                                            AIAgent.chat(last_user_text)
                                                    │
                                                    └─► Hermes tool loop
```

The handler keeps **one shared `AIAgent`** per process so Anthropic prompt
caching stays valid across turns. Bindu is the source of truth for the full
message history; the handler only passes the newest user message into
Hermes, which owns the live model state for cache hits.

Every artifact returned to the caller is DID-signed on the way out.

---

## Files

| File | Purpose |
|---|---|
| `hermes_simple_example.py` | The agent — PEP 723 script, 117 lines |
| `.env.example` | Template for required/optional env vars |
| `README.md` | You're reading it |

---

## Troubleshooting

- **`ModuleNotFoundError: run_agent`** — You're on the persistent-install path
  without hermes-agent installed. Run the `uv pip install` command from
  Option B above.
- **401 / auth errors from the model** — Your `OPENROUTER_API_KEY` isn't set,
  or the `HERMES_MODEL` you chose doesn't route through OpenRouter. Set the
  matching provider key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, …).
- **Tool calls silently missing** — Check `HERMES_TIER`. `read` intentionally
  blocks everything except web search and extract.
- **Port 3773 already in use** — Set `BINDU_PORT=4000` (or any free port)
  before launching, and update `HERMES_URL` to match.
