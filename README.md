<p align="center">
  <img src="assets/bindu_landscape.png" alt="Bindu — humans and agents, side by side" width="100%">
</p>

<div align="center">

<img alt="Bindu" src="assets/bindu_logo.png" width="80">

# Bindu

### The identity, communication, and payments layer for AI agents.

</div>

<br>

> **Write your agent in any framework. Wrap it with `bindufy()`.**
> **Ship a signed A2A microservice — identity, OAuth2, and on-chain payments — in ten lines of code.**

No infrastructure to write. No framework to rewrite. Works from Python, TypeScript, and Kotlin, and layered on two open protocols: [A2A](https://github.com/a2aproject/A2A) and [x402](https://github.com/coinbase/x402).

<div align="center">

  <p>
    <a href="README.md">English</a> ·
    <a href="i18n/README.de.md">Deutsch</a> ·
    <a href="i18n/README.es.md">Español</a> ·
    <a href="i18n/README.fr.md">Français</a> ·
    <a href="i18n/README.hi.md">हिंदी</a> ·
    <a href="i18n/README.bn.md">বাংলা</a> ·
    <a href="i18n/README.zh.md">中文</a> ·
    <a href="i18n/README.nl.md">Nederlands</a> ·
    <a href="i18n/README.ta.md">தமிழ்</a>
  </p>

  <p>
    <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
    <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
    <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
    <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
    <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
    <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img src="https://img.shields.io/github/contributors/getbindu/Bindu" alt="Contributors"></a>
    <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img src="https://hits.sh/github.com/Saptha-me/Bindu.svg" alt="Hits"></a>
  </p>

  <p>
    <a href="https://getbindu.com"><strong>Register your agent</strong></a> ·
    <a href="https://docs.getbindu.com"><strong>Documentation</strong></a> ·
    <a href="https://discord.gg/3w5zuYUuwt"><strong>Discord</strong></a>
  </p>
</div>

---

## What you get

When you wrap a handler with `bindufy(config, handler)`, the process comes up speaking standard protocols, signing every response, and ready to take payment. Grouped by what it does for you:

<br>

**Protocol — talk to the world**

| Capability | What it means |
|---|---|
| A2A JSON-RPC endpoint | Standard protocol other agents already speak. `message/send`, `tasks/get`, `message/stream` on port 3773. |
| Push notifications | Webhook callbacks on task state change — no polling required. |
| Language-agnostic | Python, TypeScript, and Kotlin SDKs share one gRPC core. Same protocol, same DID, same auth. |

<br>

**Identity & access — prove who's calling**

| Capability | What it means |
|---|---|
| DID identity (Ed25519) | Every returned artifact is signed. Callers verify with a W3C-standard DID — no shared secrets. |
| OAuth2 via Ory Hydra | Scoped tokens (`agent:read`, `agent:write`, `agent:execute`) instead of one all-or-nothing bearer. |

<br>

**Commerce & reach — get paid and be reachable**

| Capability | What it means |
|---|---|
| x402 payments | One flag and the agent charges USDC on Base before processing a request. Payment check runs before your handler. |
| Public tunnel | `expose: true` opens an FRP tunnel so your local agent is reachable from the public internet. |

---

## Install

```bash
uv add bindu
```

For a development checkout with tests:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv). An API key for at least one LLM provider (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `MINIMAX_API_KEY`) is needed to run the examples.

---

## Hello agent

The whole idea of Bindu shows up clearly in one file — build any agent you like, hand it to `bindufy()`, and your process comes up as a signed A2A microservice. The block below is complete and runnable.

```python
import os
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

# 1. Build your agent with whatever framework you prefer. Bindu doesn't
#    care what's inside — it just needs something callable.
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# 2. Tell Bindu who you are and where the agent lives. `expose: True`
#    opens a public FRP tunnel — drop it for local-only.
config = {
    "author": "you@example.com",
    "name": "research_agent",
    "description": "Research assistant with web search.",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": ["skills/question-answering"],
}

# 3. The handler contract: (messages) -> response. That's it.
def handler(messages: list[dict[str, str]]):
    return agent.run(input=messages)

# 4. bindufy() boots the HTTP server, mints your DID, registers with
#    Hydra (if auth is on), and starts accepting A2A calls.
bindufy(config, handler)
```

Run it, and the agent is live at the configured URL. Need a different port? Export `BINDU_PORT=4000` — no code change.

<p align="center">
  <img src="assets/agno-simple.png" alt="A bindufied Agno agent running on port 3773" width="780" />
</p>

<details>
<summary>TypeScript equivalent</summary>

```typescript
import { bindufy } from "@bindu/sdk";
import OpenAI from "openai";

const openai = new OpenAI();

bindufy({
  author: "you@example.com",
  name: "research_agent",
  description: "Research assistant.",
  deployment: { url: "http://localhost:3773", expose: true },
  skills: ["skills/question-answering"],
}, async (messages) => {
  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: messages.map(m => ({ role: m.role as "user" | "assistant" | "system", content: m.content })),
  });
  return response.choices[0].message.content || "";
});
```

The TypeScript SDK launches the Python core automatically. Same protocol, same DID. Full example in [`examples/typescript-openai-agent/`](examples/typescript-openai-agent/).

</details>

<details>
<summary>Calling the agent with curl</summary>

```bash
curl -X POST http://localhost:3773/ \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": "<uuid>",
    "params": {
      "message": {
        "role": "user",
        "kind": "message",
        "parts": [{"kind": "text", "text": "Hello"}],
        "messageId": "<uuid>",
        "contextId": "<uuid>",
        "taskId": "<uuid>"
      }
    }
  }'
```

Poll `tasks/get` with the same `taskId` until state is `completed`. The returned artifact carries a DID signature under `metadata["did.message.signature"]`.

</details>

---

## How it fits

So what actually happens when that `bindufy()` call executes? The handler is the only code you write. Everything else is scaffolding Bindu puts around it:

```
your handler  ──►  bindufy(config, handler)
                          │
                          ▼
                 ┌────────────────────────────────────┐
                 │  Bindu core (HTTP :3773)           │
                 │    OAuth2 (Hydra)                  │
                 │    DID verification                │
                 │    x402 payment check (optional)   │
                 │    Task manager + scheduler        │
                 └────────────────────────────────────┘
                          │
                          ▼
                 A2A-signed artifact returned to caller
```

`bindufy()` is a thin wrapper. Your handler stays pure — `(messages) -> response`. Bindu owns identity, protocol, auth, payment, storage, and scheduling.

---

## Calling a secured agent

> **TL;DR** — when `AUTH__ENABLED=true`, every call needs a Hydra bearer token *and* three `X-DID-*` headers. Python client: ~25 lines, [below](#step-2--pick-your-client). Postman: paste one script. The rest of this section unpacks why and how, and what goes wrong when it goes wrong.

The `curl` example in *Hello agent* works because auth is off by default — anyone can POST to your agent. The moment you flip `AUTH__ENABLED=true AUTH__PROVIDER=hydra`, your agent gets stricter. Every caller now has to answer two questions before the handler runs:

1. **Are you allowed to call me?** — show a valid OAuth2 token from Hydra.
2. **Are you really who you say you are?** — sign the request with a DID key.

Think of it like boarding a flight: the boarding pass (OAuth token) says "yes, you have a seat on this flight," and the passport (DID signature) says "and you really are the person on that boarding pass." The server checks both.

The full theory lives in [`docs/AUTHENTICATION.md`](docs/AUTHENTICATION.md) and [`docs/DID.md`](docs/DID.md) — plain-English, no crypto background assumed. What follows is the practical "I just want to call my agent" version.

<br>

### The three extra headers

Alongside the usual `Authorization: Bearer <hydra-jwt>`, every secured request carries:

| Header | Value |
|---|---|
| `X-DID` | your DID string, e.g. `did:bindu:you_at_example_com:myagent:<uuid>` |
| `X-DID-Timestamp` | current unix seconds (server allows 5 min skew) |
| `X-DID-Signature` | `base58( Ed25519_sign( <signing payload> ) )` |

The **signing payload** is reconstructed on the server like this:

```python
json.dumps({"body": <raw-body-string>, "did": <did>, "timestamp": <ts>}, sort_keys=True)
```

Two gotchas that will bite you until you've felt them:

- **Match Python's JSON spacing.** Python's default `json.dumps` writes `", "` and `": "` (with spaces). `JSON.stringify` in JS writes them without. If your payload serializes differently, Ed25519 sees different bytes and the server returns `reason="crypto_mismatch"`.
- **Sign what you send.** If you parse the body, modify it, re-serialize, and ship that — you signed the wrong bytes. Build the body string **once**, sign those exact bytes, send those exact bytes.

<br>

### Step 1 — get a bearer token from Hydra

The agent prints a ready-to-run curl in its startup banner. The short version:

```bash
SECRET=$(jq -r '.[].client_secret' < .bindu/oauth_credentials.json)
curl -X POST https://hydra.getbindu.com/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=did:bindu:you_at_example_com:myagent:<uuid>" \
  -d "client_secret=$SECRET" \
  -d "scope=openid offline agent:read agent:write"
```

The response has an `access_token`. It's good for about an hour — cache it, refetch when you need it.

<br>

### Step 2 — pick your client

**Python — the shortest working example.** Reads the agent's own keys (Bindu writes them to `.bindu/` on first boot), signs a request, polls for the result. Self-call works because the agent's keys *are* a valid caller identity.

```python
import base58, httpx, json, time, uuid
from pathlib import Path
from cryptography.hazmat.primitives import serialization

# 1. Load the keys Bindu wrote on first boot
priv  = serialization.load_pem_private_key(Path(".bindu/private.pem").read_bytes(), password=None)
creds = next(iter(json.loads(Path(".bindu/oauth_credentials.json").read_text()).values()))
did   = creds["client_id"]            # DID doubles as the Hydra client_id

# 2. Exchange credentials for a short-lived JWT
bearer = httpx.post("https://hydra.getbindu.com/oauth2/token", data={
    "grant_type": "client_credentials",
    "client_id": creds["client_id"], "client_secret": creds["client_secret"],
    "scope": "openid offline agent:read agent:write",
}).json()["access_token"]

# 3. Build the body ONCE — these are the bytes we'll sign AND send
tid = str(uuid.uuid4())
body = json.dumps({
    "jsonrpc": "2.0", "method": "message/send", "id": str(uuid.uuid4()),
    "params": {"message": {
        "role": "user", "kind": "message",
        "parts": [{"kind": "text", "text": "Hello!"}],
        "messageId": str(uuid.uuid4()), "contextId": str(uuid.uuid4()), "taskId": tid,
    }},
})

# 4. Sign: base58(Ed25519( json.dumps({body,did,timestamp}, sort_keys=True) ))
ts      = int(time.time())
payload = json.dumps({"body": body, "did": did, "timestamp": ts}, sort_keys=True)
sig     = base58.b58encode(priv.sign(payload.encode())).decode()

# 5. Fire it
r = httpx.post("http://localhost:3773/", content=body, headers={
    "Content-Type":    "application/json",
    "Authorization":   f"Bearer {bearer}",
    "X-DID":           did,
    "X-DID-Timestamp": str(ts),
    "X-DID-Signature": sig,
})
print(r.status_code, r.json())
```

For a full-featured version with polling and error handling, see [`examples/hermes_agent/call.py`](examples/hermes_agent/call.py).

<br>

**Postman — paste one script into your collection.**

1. Open your collection → **Pre-request Script** tab → paste the contents of [`docs/postman-did-signing.js`](docs/postman-did-signing.js).
2. Set two collection variables: `bindu_did` (your DID string) and `bindu_did_seed` (your 32-byte Ed25519 seed, base64-encoded).
3. Add an `Authorization: Bearer {{bindu_bearer}}` header and drop your Hydra token into `bindu_bearer`.
4. Hit Send. The script signs the exact body bytes Postman is about to send and sets the three `X-DID-*` headers for you.

Requires Postman Desktop v11+ (needs Ed25519 in `crypto.subtle`).

<br>

**Plain curl — technically possible, usually painful.** The signature depends on the body bytes you're about to send, so you need a helper script to compute the signature first, then substitute it into the curl call. If you're doing this, you're probably better off using the Python client above.

<br>

### When signatures fail

The server logs one of three reasons. If your request gets rejected with a 403, ask the operator (or check the server log yourself):

| Log says | What it means | Fix |
|---|---|---|
| `timestamp_out_of_window` | Your `X-DID-Timestamp` is more than 5 min off the server's clock, or you reused an old timestamp | Recompute `int(time.time())` on every request |
| `malformed_input` | The base58 decoding of the signature or public key failed | Check the `X-DID-Signature` isn't URL-encoded, truncated, or wrapped in quotes |
| `crypto_mismatch` | The bytes you signed ≠ the bytes you sent | Rebuild the payload with `sort_keys=True` and Python's default JSON spacing; sign the raw body string once and send the same bytes |

One sharper failure mode we hit in testing: if `crypto_mismatch` persists and you're *sure* your bytes match, Hydra's stored public key for this DID may be stale from an older registration. Fix: stop the agent, delete `.bindu/oauth_credentials.json`, restart — Hydra's client record will be refreshed with the current keys.

---

## Gateway — multi-agent orchestration

A single `bindufy()`-wrapped agent is a microservice. The **Bindu Gateway** is a task-first orchestrator that sits on top: give it a user question and a catalog of A2A agents, and a planner LLM decomposes the work, calls the right agents over A2A, and streams results back as Server-Sent Events. No DAG engine, no separate orchestrator service — the planner's LLM picks tools per turn.

What you get beyond a single agent:

- **One endpoint: `POST /plan`** — hand it a question and an agent catalog, get streamed steps.
- **Agent catalog per request** — external systems pass the list of agents, skills, and endpoints. No fleet hosting in the gateway itself.
- **Session persistence (Supabase)** — Postgres-backed with compaction, revert, and multi-turn history.
- **Native TypeScript A2A** — no Python subprocess, no `@bindu/sdk` dependency in the gateway.
- **Optional DID signing + Hydra integration** — gateway identity end-to-end.

Minimal quickstart:

```bash
cd gateway
npm install
cp .env.example .env.local         # fill SUPABASE_*, GATEWAY_API_KEY, OPENROUTER_API_KEY
npm run dev                        # → http://localhost:3774
curl -sS http://localhost:3774/health
```

Apply the two Supabase migrations first (`gateway/migrations/001_init.sql`, `002_compaction_revert.sql`). Full walkthrough and operator reference live in [`gateway/README.md`](gateway/README.md) and [`docs/GATEWAY.md`](docs/GATEWAY.md) (45-minute end-to-end: clean clone → three chained agents → authoring a recipe → DID signing).

Gateway documentation:

| Topic | Link |
|---|---|
| Overview | [docs.getbindu.com/bindu/gateway/overview](https://docs.getbindu.com/bindu/gateway/overview) |
| Quickstart | [docs.getbindu.com/bindu/gateway/quickstart](https://docs.getbindu.com/bindu/gateway/quickstart) |
| Multi-agent planning | [docs.getbindu.com/bindu/gateway/multi-agent](https://docs.getbindu.com/bindu/gateway/multi-agent) |
| Recipes (progressive-disclosure playbooks) | [docs.getbindu.com/bindu/gateway/recipes](https://docs.getbindu.com/bindu/gateway/recipes) |
| Identity (DID signing, Hydra) | [docs.getbindu.com/bindu/gateway/identity](https://docs.getbindu.com/bindu/gateway/identity) |
| Production deployment | [docs.getbindu.com/bindu/gateway/production](https://docs.getbindu.com/bindu/gateway/production) |
| API reference | [docs.getbindu.com/api/introduction](https://docs.getbindu.com/api/introduction) |

For a runnable multi-agent demo, see [`examples/gateway_test_fleet/`](examples/gateway_test_fleet/) — five small agents on local ports, one gateway, one query.

---

## Supported frameworks and examples

Bring whichever agent framework you already like. You hand Bindu a handler; it gives you a signed A2A microservice. Same flow regardless of what's inside the handler.

<br>

| Language | Frameworks tested in this repo |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2) · [Agno](https://github.com/agno-agi/agno) · [CrewAI](https://github.com/joaomdmoura/crewAI) · [Hermes Agent](https://github.com/NousResearch/hermes-agent) · [LangChain](https://github.com/langchain-ai/langchain) · [LangGraph](https://github.com/langchain-ai/langgraph) · [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node) · [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **Any other language** | via the [gRPC core](docs/grpc/) — add an SDK in a few hundred lines |

Compatible with any LLM provider that speaks the OpenAI or Anthropic API: [OpenRouter](https://openrouter.ai/) (100+ models), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com), and others.

<br>

### A handful of examples to get you started

Five that cover the spectrum of what Bindu can do. All 20+ runnable examples live under [`examples/`](examples/).

| Example | What it shows |
|---|---|
| [Agent Swarm](examples/agent_swarm/) | Multi-agent collaboration — a small "society" of Agno agents delegating work to each other. |
| [Premium Advisor](examples/premium-advisor/) | **x402 payments** — caller has to pay USDC on Base before the handler runs. |
| [Hermes via Bindu](examples/hermes_agent/) | **Third-party framework interop** — Nous Research's Hermes agent bindufied in ~90 lines. |
| [Gateway Test Fleet](examples/gateway_test_fleet/) | Five small agents + one gateway — the multi-agent orchestration story end-to-end. |
| [TypeScript OpenAI Agent](examples/typescript-openai-agent/) | **Polyglot proof** — a TS agent bindufied with the Bindu TS SDK; no Python to write. |

**See the full catalog:** [`examples/`](examples/) — 20+ agents covering CSV analysis, PDF Q&A, speech-to-text, web scraping, cybersecurity newsletters, multi-lingual collab, blog writing, and more.

Missing a framework you use? Open an issue or ask on [Discord](https://discord.gg/3w5zuYUuwt).

---

## Demo

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu demo video" width="640" />
  </a>
</div>

A built-in chat UI is available at `http://localhost:5173` after running `cd frontend && npm run dev`.

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu agent UI" width="640" />
</p>

---

## Core features

Everything below is optional and modular — the minimal install is just the A2A server. Each row links to a dedicated guide in [`docs/`](docs/).

<br>

**Identity & access**

| Feature | Guide |
|---|---|
| Decentralized Identifiers (DIDs) | [DID.md](docs/DID.md) |
| Authentication (Ory Hydra OAuth2) | [AUTHENTICATION.md](docs/AUTHENTICATION.md) |

<br>

**Protocol & infrastructure**

| Feature | Guide |
|---|---|
| Skills system | [SKILLS.md](docs/SKILLS.md) |
| Agent negotiation | [NEGOTIATION.md](docs/NEGOTIATION.md) |
| Push notifications | [NOTIFICATIONS.md](docs/NOTIFICATIONS.md) |
| PostgreSQL storage | [STORAGE.md](docs/STORAGE.md) |
| Redis scheduler | [SCHEDULER.md](docs/SCHEDULER.md) |
| Language-agnostic via gRPC | [GRPC_LANGUAGE_AGNOSTIC.md](docs/GRPC_LANGUAGE_AGNOSTIC.md) |

<br>

**Commerce & reach**

| Feature | Guide |
|---|---|
| x402 payments (USDC on Base) | [PAYMENT.md](docs/PAYMENT.md) |
| Tunneling (local dev only) | [TUNNELING.md](docs/TUNNELING.md) |

<br>

**Reliability & operations**

| Feature | Guide |
|---|---|
| Retry with exponential backoff | [Retry docs](https://docs.getbindu.com/bindu/learn/retry/overview) |
| Observability (OpenTelemetry, Sentry) | [OBSERVABILITY.md](docs/OBSERVABILITY.md) |
| Health check and metrics | [HEALTH_METRICS.md](docs/HEALTH_METRICS.md) |

---

## Testing

Bindu targets 70% test coverage (goal: 80%+):

```bash
uv run pytest tests/unit/ -v                                    # fast unit tests
uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC E2E
uv run pytest -n auto --cov=bindu --cov-report=term-missing    # full suite
```

CI runs unit tests, gRPC E2E, and TypeScript SDK build on every PR. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Known issues

If you're running Bindu in production, read [`bugs/known-issues.md`](bugs/known-issues.md) first. It's a per-subsystem catalog with workarounds. Postmortems for fixed bugs live under [`bugs/core/`](bugs/core/), [`bugs/gateway/`](bugs/gateway/), [`bugs/sdk/`](bugs/sdk/), and [`bugs/frontend/`](bugs/frontend/).

Current high-severity items:

| Subsystem | Slug | Symptom |
|---|---|---|
| Core | [`x402-middleware-fails-open-on-body-parse`](bugs/known-issues.md#x402-middleware-fails-open-on-body-parse) | Malformed JSON body bypasses payment check |
| Core | [`x402-no-replay-prevention`](bugs/known-issues.md#x402-no-replay-prevention) | One payment buys unlimited work until `validBefore` |
| Core | [`x402-no-signature-verification`](bugs/known-issues.md#x402-no-signature-verification) | EIP-3009 signature is never verified |
| Core | [`x402-balance-check-skipped-on-missing-contract-code`](bugs/known-issues.md#x402-balance-check-skipped-on-missing-contract-code) | Misconfigured RPC silently skips balance check |
| Gateway | [`context-window-hardcoded`](bugs/known-issues.md#context-window-hardcoded) | Compaction threshold assumes a 200k-token window |
| Gateway | [`poll-budget-unbounded-wall-clock`](bugs/known-issues.md#poll-budget-unbounded-wall-clock) | `sendAndPoll` can stall 5 minutes per tool call |
| Gateway | [`no-session-concurrency-guard`](bugs/known-issues.md#no-session-concurrency-guard) | Two `/plan` calls on the same session tangle histories |

Found a new issue? Open a GitHub Issue referencing the slug (e.g. *"Fixes `context-window-hardcoded`"*). Fixed one? Remove its entry from `known-issues.md` and add a dated postmortem — see [`bugs/README.md`](bugs/README.md) for the template.

---

## Troubleshooting

<details>
<summary>Common issues</summary>

| Issue | Fix |
|---|---|
| `uv: command not found` | Restart your shell after installing uv. |
| `Python version not supported` | Install Python 3.12+ from [python.org](https://www.python.org/downloads/) or via `pyenv`. |
| `bindu: command not found` | Activate your virtualenv: `source .venv/bin/activate`. |
| `Port 3773 already in use` | Set `BINDU_PORT=4000`, or override with `BINDU_DEPLOYMENT_URL=http://localhost:4000`. |
| `ModuleNotFoundError` | Run `uv sync --dev`. |
| Pre-commit fails | Run `pre-commit run --all-files`. |
| `Permission denied` (macOS) | `xattr -cr .` to clear extended attributes. |

Reset the environment:

```bash
rm -rf .venv && uv venv --python 3.12.9 && uv sync --dev
```

On Windows PowerShell you may need `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`.

</details>

---

## Contributing

Clone, set up, and run the pre-commit hooks:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

Discussion and help happen on [Discord](https://discord.gg/3w5zuYUuwt). See [`.github/contributing.md`](.github/contributing.md) for the full guide. There's an open list of agents we'd like to see bindufied — [contribute one](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link).

---

## Maintainers

<table>
  <tr>
    <td align="center"><a href="https://github.com/raahulrahl"><img src="https://avatars.githubusercontent.com/u/157174139?v=4" width="80" alt="Raahul Dutta"/><br /><sub><b>Raahul Dutta</b></sub></a></td>
    <td align="center"><a href="https://github.com/Paraschamoli"><img src="https://avatars.githubusercontent.com/u/157124537?v=4" width="80" alt="Paras Chamoli"/><br /><sub><b>Paras Chamoli</b></sub></a></td>
    <td align="center"><a href="https://github.com/chandan-1427"><img src="https://avatars.githubusercontent.com/u/202320492?v=4" width="80" alt="Chandan"/><br /><sub><b>Chandan</b></sub></a></td>
  </tr>
</table>

---

## Acknowledgements

Bindu stands on the shoulders of:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/library/emoji-1F33B/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

---

## License

Apache 2.0. See [LICENSE.md](LICENSE.md).

<p align="center">
  <a href="https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date">
    <img src="https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date" alt="Star history">
  </a>
</p>

<p align="center">
  <sub>
    Crafted between Amsterdam and India · open source under Apache 2.0 ·
    <a href="https://getbindu.com">getbindu.com</a>
  </sub>
</p>
