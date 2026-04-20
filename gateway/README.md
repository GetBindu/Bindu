# Bindu Gateway

A task-first orchestrator that sits between an **external system** and one or more **Bindu A2A agents**. Takes a user question + an agent catalog, plans the work with an LLM, calls downstream Bindu agents via the A2A polling protocol, and streams results back as Server-Sent Events.

- **One endpoint:** `POST /plan`
- **Planner = LLM:** no DAG engine, no separate orchestrator service. The planner agent's LLM decomposes the question and picks tools per turn.
- **Agent catalog per request:** external system provides the list of agents + skills + endpoints. No fleet hosting here.
- **Sessions persist in Supabase:** Postgres-backed with compaction + revert + multi-turn history.
- **Native TS A2A 0.3.0:** no Python subprocess, no `@bindu/sdk` dependency. Calibrated against live deployed Bindu agents via Phase 0 dry-run fixtures.

For design rationale, see [`plans/PLAN.md`](./plans/PLAN.md). Phase-by-phase detail lives in `plans/phase-*.md`.

---

## Status

Phase 1 Days 1–9 shipped. Core gateway is functionally complete:

- ✅ Bus, Config, DB (Supabase), Auth, Permission, Provider (Anthropic/OpenAI)
- ✅ Tool registry + Skill/Agent loaders
- ✅ Session module (message, state, LLM stream, the **loop**, compaction, summary, revert, overflow detection)
- ✅ Bindu protocol: Zod types for Message/Part/Artifact/Task/AgentCard, mixed-casing normalize, DID parse, JSON-RPC envelope, BinduError classification
- ✅ Bindu identity: ed25519 verify (against real Phase 0 signatures)
- ✅ Bindu polling client: `message/send` + `tasks/get` loop with camelCase-first + `-32700`/`-32602` retry flip
- ✅ Planner: agent catalog → dynamic tools, compaction hook before each turn, `<remote_content>` envelope
- ✅ Hono server + `/plan` SSE handler + `/health`
- ✅ Layer-graph wiring in `src/index.ts`
- ✅ **23 passing tests**, including integration against an in-process mock Bindu agent

What's not done yet (Phase 2+ future commits):

- Live smoke test against real Supabase + real Anthropic + real Bindu
- Reconnect / `tasks/resubscribe`, tenancy enforcement, circuit breakers, rate limits, observability (Phase 2)
- Inbound Bindu server + DID signing + mTLS (Phase 3)
- Registry + trust scoring + cycle limits (Phase 4)
- Payments, negotiation orchestrator, push notifications (Phase 5)

---

## Quickstart

### Prerequisites

- **Node 22+** (tsx runs the TypeScript directly; no build step in dev)
- **Supabase project** (free tier is fine). Copy `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`.
- **Anthropic API key** (or OpenAI) for the planner LLM.

### 1. Install deps

```bash
cd gateway
npm install
```

### 2. Apply the database schema

From the Supabase SQL editor, run in order:

```
migrations/001_init.sql            # gateway_sessions, gateway_messages, gateway_tasks + RLS
migrations/002_compaction_revert.sql  # adds compacted/reverted flags + compaction_summary
```

Or with the Supabase CLI:

```bash
bunx supabase link --project-ref <your-ref>
bunx supabase db push
```

### 3. Configure

Copy `.env.example` → `.env.local` and fill in:

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
GATEWAY_API_KEY=dev-key-change-me
ANTHROPIC_API_KEY=sk-ant-...
GATEWAY_PORT=3774
```

### 4. Run

```bash
npm run dev       # tsx watch src/index.ts
# OR
npm start         # tsx src/index.ts
```

Health check:

```bash
curl http://localhost:3774/health
```

### 5. Fire a plan

```bash
curl -N -X POST http://localhost:3774/plan \
  -H "Authorization: Bearer dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me about yourself",
    "agents": [
      {
        "name": "echo",
        "endpoint": "http://localhost:3773",
        "auth": {"type": "none"},
        "skills": [
          {"id": "question-answering-v1", "description": "Answer questions"}
        ]
      }
    ]
  }'
```

You'll see SSE frames like:

```
event: plan
data: {"plan_id":"…","session_id":"…"}

event: task.started
data: {"task_id":"…","agent":"echo","skill":"question-answering-v1","input":"\"Tell me about yourself\""}

event: task.artifact
data: {"task_id":"…","content":"<remote_content agent=\"echo\" verified=\"unknown\">…</remote_content>"}

event: task.finished
data: {"task_id":"…","state":"completed"}

event: final
data: {"session_id":"…","stop_reason":"stop","usage":{…}}

event: session
data: {"session_id":"…","external_session_id":null,"created":true}

event: done
data: {}
```

---

## Architecture

Three-layer pipeline, one process:

```
Hono HTTP (src/server + src/api)
  └── POST /plan → Planner.startPlan(request)
       └── SessionPrompt.prompt(sessionID, agent, parts, tools)
            ├── SessionCompaction.compactIfNeeded  (before each turn)
            ├── Provider.model(model)              (AI SDK handle)
            ├── LLM.stream(model, messages, tools) (streamText wrapper)
            │    └── for each tool call:
            │         Bindu.Client.callPeer({peer, skill, input})
            │           ├── auth headers (bearer | bearer_env | none)
            │           ├── POST / method=message/send
            │           ├── poll message/tasks/get (camelCase, -32700 flip)
            │           ├── verify DID signatures when trust.verifyDID
            │           └── return Task → ExecuteResult
            └── Session persisted to Supabase via DB.Service
```

See [`plans/PLAN.md`](./plans/PLAN.md) §Architecture for the full picture.

---

## DID signing for downstream peers

The gateway can sign outbound A2A requests with an Ed25519 identity so DID-enforcing Bindu peers accept them. Needed for any peer you configure with `auth.type = "did_signed"`; ignored otherwise.

### Two modes

| Mode | When to use | Setup |
|---|---|---|
| **Auto** (recommended) | Single Hydra shared by the gateway and its peers | Set identity + Hydra URL env vars; gateway self-registers and auto-acquires tokens |
| **Manual** (federated) | Peers use different Hydras | Set identity env vars; pre-register manually with each peer's Hydra; stash per-peer tokens in env vars |

### Auto mode setup

```bash
# Identity (same for both modes)
export BINDU_GATEWAY_DID_SEED="$(python -c 'import os,base64;print(base64.b64encode(os.urandom(32)).decode())')"
export BINDU_GATEWAY_AUTHOR=ops@example.com
export BINDU_GATEWAY_NAME=gateway

# Hydra auto-registration
export BINDU_GATEWAY_HYDRA_ADMIN_URL=http://hydra:4445
export BINDU_GATEWAY_HYDRA_TOKEN_URL=http://hydra:4444/oauth2/token
# export BINDU_GATEWAY_HYDRA_SCOPE="openid offline agent:read agent:write"  # optional
```

On boot the gateway:

1. Derives its DID and public key from the seed. Logs both.
2. Registers itself with Hydra as an OAuth client (`client_id` = the DID, `metadata.public_key` = the base58 public key). Idempotent — safe to restart.
3. Acquires an access token via `client_credentials`. In-memory cache + proactive refresh 30s before expiry.

Peer config for auto mode:

```json
{ "url": "http://agent:3773", "auth": { "type": "did_signed" } }
```

No `tokenEnvVar` needed — the gateway pulls the token from its cached Hydra provider.

### Manual mode setup (federated)

Each peer uses its own Hydra. The gateway holds a token per peer, supplied via env vars:

```bash
# Identity only — no Hydra auto vars
export BINDU_GATEWAY_DID_SEED="..."
export BINDU_GATEWAY_AUTHOR=ops@example.com
export BINDU_GATEWAY_NAME=gateway

# One token per peer
export RESEARCH_HYDRA_TOKEN="$(hydra token client ...)"
export SUPPORT_HYDRA_TOKEN="$(hydra token client ...)"
```

Peer config:

```json
{ "url": "http://research:3773", "auth": { "type": "did_signed", "tokenEnvVar": "RESEARCH_HYDRA_TOKEN" } },
{ "url": "http://support:3773",  "auth": { "type": "did_signed", "tokenEnvVar": "SUPPORT_HYDRA_TOKEN" } }
```

Mix-and-match is fine too: a peer with `tokenEnvVar` set uses that env var even when the auto provider is also configured (peer-scoped wins).

### What happens on the wire

For every outbound call to a `did_signed` peer:

1. Serialize the JSON-RPC request body once.
2. Sign those exact bytes with the gateway's private key. Matches Python's `json.dumps(payload, sort_keys=True)` byte-for-byte — see `src/bindu/identity/local.ts`.
3. Send `Authorization: Bearer <token>` + `X-DID`, `X-DID-Signature`, `X-DID-Timestamp` headers on the same request.

### Failure modes — all fail fast with clear errors

| Scenario | When | Error |
|---|---|---|
| Seed malformed | Boot | `BINDU_GATEWAY_DID_SEED must decode to exactly 32 bytes` |
| Partial identity config | Boot | `Partial DID identity config — set all three or none` |
| Partial Hydra config (admin without token or vice versa) | Boot | `Partial Hydra config — set both or neither` |
| Hydra admin unreachable | Boot | `Hydra admin GET /admin/clients/... returned 503: ...` |
| `did_signed` peer but no identity | First call | `did_signed peer requires a gateway LocalIdentity` |
| `did_signed` peer with no tokenEnvVar and no provider | First call | clear error naming both options |

Peers configured with `none` / `bearer` / `bearer_env` continue to work with or without DID identity. Leave the env vars unset if no peer needs DID signing.

---

## Tests

```bash
npm test           # vitest run
npm run test:watch # vitest watch
npm run typecheck  # tsc --noEmit
```

| Test file | Count | What it covers |
|---|---|---|
| `tests/bindu/protocol.test.ts` | 12 | Parses Phase 0 fixtures; casing normalize round-trips; DID parse; BinduError classification |
| `tests/bindu/identity.test.ts` | 4 | Verifies a real signature against the captured echo-agent DID Doc (tamper detection, malformed signature) |
| `tests/bindu/poll.test.ts` | 4 | Mock-fetch polling: submitted→completed, `-32700` casing flip, `input-required` needsAction, `-32013` InsufficientPermissions |
| `tests/integration/bindu-client-e2e.test.ts` | 3 | In-process mock Bindu agent on a random port; end-to-end `sendAndPoll` round-trip |

**Phase 0 dry-run fixtures** live at `../scripts/dryrun-fixtures/echo-agent/` and were captured against a running `bindu` Python reference agent. The protocol tests parse them bit-for-bit so any schema drift fails CI immediately.

---

## Repo layout

```
gateway/
├── .env.example              # env var template
├── package.json              # @bindu/gateway
├── tsconfig.json             # strict, ES2023, path aliases
├── vitest.config.ts          # test config (loads .env.local)
├── migrations/               # Supabase SQL
│   ├── 001_init.sql
│   └── 002_compaction_revert.sql
├── agents/                   # markdown+YAML agent configs
│   └── planner.md            # the default planner system prompt
├── plans/                    # Design docs (PLAN.md + phase-*.md)
├── src/
│   ├── _shared/              # vendored @opencode-ai/shared
│   ├── effect/               # Effect runtime glue (from OpenCode)
│   ├── util/                 # logger, filesystem, error helpers (from OpenCode)
│   ├── id/                   # ID generators
│   ├── global/               # XDG paths
│   ├── bus/                  # FRESH — typed event bus
│   ├── config/               # FRESH — hierarchical config loader
│   ├── db/                   # FRESH — Supabase adapter
│   ├── auth/                 # FRESH — credential keystore
│   ├── permission/           # FRESH — wildcard ruleset evaluator
│   ├── provider/             # FRESH — AI SDK handle lookup
│   ├── skill/                # FRESH — markdown skill loader
│   ├── agent/                # FRESH — agent.md loader
│   ├── tool/                 # FRESH — Tool.define + registry
│   ├── session/              # FRESH — message, service, LLM stream,
│   │                         #         the loop, compaction, revert
│   ├── bindu/                # FRESH — Bindu A2A: protocol, identity,
│   │                         #         auth, client
│   ├── planner/              # FRESH — agent catalog → dynamic tools
│   ├── server/               # FRESH — Hono shell + /health
│   ├── api/                  # FRESH — POST /plan + SSE emitter
│   └── index.ts              # FRESH — Layer graph + boot
└── tests/
    ├── bindu/                # protocol, identity, poll unit tests
    ├── helpers/              # mock-bindu-agent.ts
    └── integration/          # bindu-client-e2e.test.ts
```

**Fresh = Bindu-native, written for the gateway.** **From OpenCode** = copied + trimmed of coding-specific features (no LSP, no git, no bash/edit tools, no IDE integration).

---

## License + credits

Apache-2.0 (matches the Bindu monorepo).

The gateway borrows the Effect runtime glue and utility modules from [sst/opencode](https://github.com/sst/opencode) (MIT). Vendored at `src/_shared/` and `src/{effect,util,id,global}/`. See [`plans/PLAN.md`](./plans/PLAN.md) §Fork & Extract Plan for the full list of what was copied vs rewritten.
