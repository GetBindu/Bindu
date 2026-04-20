# Bindu Gateway

A task-first orchestrator that sits between an **external system** and one or more **Bindu A2A agents**. Takes a user question + an agent catalog, plans the work with an LLM, calls downstream Bindu agents via the A2A polling protocol, and streams results back as Server-Sent Events.

- **One endpoint:** `POST /plan`
- **Planner = LLM:** no DAG engine, no separate orchestrator service. The planner agent's LLM decomposes the question and picks tools per turn.
- **Agent catalog per request:** external system provides the list of agents + skills + endpoints. No fleet hosting here.
- **Sessions persist in Supabase:** Postgres-backed with compaction + revert + multi-turn history.
- **Native TS A2A:** no Python subprocess, no `@bindu/sdk` dependency.

## New here?

**Read [`docs/STORY.md`](./docs/STORY.md) first.** It's a 45-minute end-to-end walkthrough that goes from a clean clone to running three chained agents, authoring a recipe, and turning on DID signing. Written for readers with no prior AI-agent knowledge.

This README is the **operator's reference** — configuration, troubleshooting, and pointers into source. The narrative lives in STORY.md.

---

## Quickstart

```bash
cd gateway
npm install
cp .env.example .env.local    # fill in SUPABASE_*, GATEWAY_API_KEY, OPENROUTER_API_KEY
npm run dev
```

Apply the two Supabase migrations first (`migrations/001_init.sql`, `migrations/002_compaction_revert.sql`). Full environment list below.

Health check:

```bash
curl -sS http://localhost:3774/health
```

Returns a detailed JSON payload describing the gateway process — version, planner model, identity (if configured), recipe count, Node/platform details, and uptime. Matches the shape of the per-agent Bindu health payload with gateway-appropriate fields. See [`openapi.yaml`](./openapi.yaml) §HealthResponse for the full schema; the interesting fields:

```json
{
  "version": "0.1.0",
  "health": "healthy",
  "runtime": {
    "storage_backend": "Supabase",
    "bus_backend": "EffectPubSub",
    "planner": {
      "model": "openrouter/anthropic/claude-sonnet-4.6",
      "provider": "openrouter",
      "model_id": "anthropic/claude-sonnet-4.6",
      "temperature": 0.3,
      "top_p": null,
      "max_steps": 10
    },
    "recipe_count": 2,
    "did_signing_enabled": true,
    "hydra_integrated": true
  },
  "application": {
    "name": "@bindu/gateway",
    "session_mode": "stateful",
    "gateway_did": "did:bindu:ops_at_example_com:gateway:47191e40-3e91-2ef4-d001-b8d005680279",
    "gateway_id": "47191e40-3e91-2ef4-d001-b8d005680279",
    "author": "ops_at_example_com"
  },
  "system": {
    "node_version": "v22.5.0",
    "platform": "darwin",
    "architecture": "arm64",
    "environment": "development"
  },
  "status": "ok",
  "ready": true,
  "uptime_seconds": 23.3
}
```

For a runnable multi-agent walkthrough, see [`docs/STORY.md`](./docs/STORY.md) §Chapter 2-3.

---

## Configuration

### Required environment variables

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Session store — Postgres project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (treat as secret) |
| `GATEWAY_API_KEY` | Bearer token that callers must send |
| `OPENROUTER_API_KEY` | Planner LLM provider |

### Optional environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GATEWAY_PORT` | `3774` | HTTP port |
| `GATEWAY_HOSTNAME` | `0.0.0.0` | Bind host |
| `BINDU_GATEWAY_DID_SEED` | unset | Ed25519 private key seed (base64, 32 bytes) |
| `BINDU_GATEWAY_AUTHOR` | unset | Owner email for DID |
| `BINDU_GATEWAY_NAME` | unset | Short DID name component |
| `BINDU_GATEWAY_HYDRA_ADMIN_URL` | unset | Hydra admin API (auto-register on boot) |
| `BINDU_GATEWAY_HYDRA_TOKEN_URL` | unset | Hydra token endpoint |
| `BINDU_GATEWAY_HYDRA_SCOPE` | `openid offline agent:read agent:write` | OAuth scopes |

See `.env.example` for the full template.

### Config file

Some settings live in a TOML/JSON config file (path resolved hierarchically like OpenCode). Source of truth: [`src/config/schema.ts`](./src/config/schema.ts) — defaults are inline.

---

## Routes

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/plan` | bearer | Open a plan or resume a session; streams SSE |
| `GET` | `/health` | none | Liveness + config probe |
| `GET` | `/.well-known/did.json` | none | Self-published DID document (only when DID identity is configured) |

Full request/response contract with examples: [`openapi.yaml`](./openapi.yaml). Paste into [Swagger UI](https://editor.swagger.io) or Redoc to click through.

---

## Recipes

Recipes are markdown playbooks the planner lazy-loads when a task matches. Only metadata (`name` + `description`) sits in the system prompt; the full body is fetched on demand via the `load_recipe` tool. Pattern borrowed from [OpenCode Skills](https://opencode.ai/docs/skills/), renamed to avoid collision with A2A `SkillRequest` (an agent capability on the `/plan` request body).

**Author one in two minutes** — see [`docs/STORY.md`](./docs/STORY.md) §Chapter 4 for the walkthrough. The reference:

### Layouts

```
gateway/recipes/foo.md                 flat recipe, no bundled files
gateway/recipes/bar/RECIPE.md          bundled recipe — siblings like
gateway/recipes/bar/scripts/run.sh     scripts/, reference/ are surfaced
gateway/recipes/bar/reference/notes.md to the planner when bar loads
```

### Frontmatter

```yaml
---
name: my-recipe                    # required, unique; cannot start with "call_"
description: One-line summary      # required (non-empty) — this is the hook
                                   # the planner reads when deciding to load
tags: [domain, workflow]           # optional, surfaced in verbose listings
triggers: [keyword1, keyword2]     # optional planner hints
---

# Playbook body — free-form markdown the planner follows after loading.
```

### Per-agent visibility

Agents (in `gateway/agents/*.md`) respect `permission.recipe:` rules:

```yaml
permission:
  recipe:
    "secret-*": "deny"     # hide matching recipes from this agent
    "*": "allow"           # everything else visible
```

Default action is `allow` — an agent with no `recipe:` rules sees everything.

### Source pointers

- Loader: [`src/recipe/index.ts`](./src/recipe/index.ts)
- `load_recipe` tool: [`src/tool/recipe.ts`](./src/tool/recipe.ts)
- Seed recipes: [`recipes/`](./recipes/)

---

## DID signing for downstream peers

For peers configured with `auth.type = "did_signed"`, the gateway signs each outbound A2A request with an Ed25519 identity. Peers verify against the gateway's public key (published at `/.well-known/did.json`) and reject mismatches.

**Full walkthrough** — [`docs/STORY.md`](./docs/STORY.md) §Chapter 5. The reference:

### Two modes

| Mode | When to use | Setup |
|---|---|---|
| **Auto** (recommended) | Single Hydra shared by the gateway and its peers | Set identity + Hydra URL env vars; gateway self-registers and auto-acquires tokens |
| **Manual** (federated) | Peers use different Hydras | Set identity env vars only; pre-register with each peer's Hydra out of band; stash per-peer tokens in env vars; use `tokenEnvVar` on the peer's `auth` block |

### Peer config — auto mode

```json
{ "url": "http://agent:3773", "auth": { "type": "did_signed" } }
```

### Peer config — manual mode

```json
{ "url": "http://research:3773", "auth": { "type": "did_signed", "tokenEnvVar": "RESEARCH_HYDRA_TOKEN" } }
```

A peer-scoped `tokenEnvVar` wins over the auto provider, so mixing is fine.

### Wire format

For every outbound `did_signed` call:

1. Serialize the JSON-RPC request body once (matches Python's `json.dumps(payload, sort_keys=True)` byte-for-byte — see [`src/bindu/identity/local.ts`](./src/bindu/identity/local.ts)).
2. Sign those exact bytes with the gateway's private key.
3. Attach `Authorization: Bearer <token>` + `X-DID`, `X-DID-Signature`, `X-DID-Timestamp` headers.

### Failure modes

| Scenario | When | Error |
|---|---|---|
| Seed malformed | Boot | `BINDU_GATEWAY_DID_SEED must decode to exactly 32 bytes` |
| Partial identity config | Boot | `Partial DID identity config — set all three or none` |
| Partial Hydra config | Boot | `Partial Hydra config — set both or neither` |
| Hydra admin unreachable | Boot | `Hydra admin GET /admin/clients/... returned 503: ...` |
| `did_signed` peer, no identity | First call | `did_signed peer requires a gateway LocalIdentity` |
| `did_signed` peer, no tokenEnvVar, no provider | First call | names both options in the error |

Peers configured with `none` / `bearer` / `bearer_env` continue to work with or without DID identity — leave the env vars unset if no peer needs signing.

---

## Tests

```bash
npm test           # vitest run
npm run test:watch # vitest watch
npm run typecheck  # tsc --noEmit
```

Unit + integration coverage across bindu/, recipe/, planner/, session/, api/, provider/. Check the current count with `npm test`; the suite is under two seconds.

**Phase 0 dry-run fixtures** live at `../scripts/dryrun-fixtures/echo-agent/` and were captured against a running `bindu` Python reference agent. The protocol tests parse them bit-for-bit so any schema drift fails CI immediately.

---

## Repo layout

```
gateway/
├── .env.example              # env var template
├── openapi.yaml              # machine-readable API contract
├── package.json              # @bindu/gateway
├── tsconfig.json             # strict, ES2023, path aliases
├── vitest.config.ts          # test config (loads .env.local)
├── docs/
│   └── STORY.md              # end-to-end walkthrough — the primary read
├── migrations/               # Supabase SQL
├── agents/                   # markdown+YAML agent configs
│   └── planner.md            # the default planner system prompt
├── recipes/                  # markdown playbooks (progressive disclosure)
├── src/
│   ├── _shared/, effect/, util/, id/, global/    # vendored from OpenCode
│   ├── bus/                  # typed event bus
│   ├── config/               # hierarchical config loader
│   ├── db/                   # Supabase adapter
│   ├── auth/                 # credential keystore
│   ├── permission/           # wildcard ruleset evaluator
│   ├── provider/             # AI SDK handle lookup (OpenRouter)
│   ├── recipe/               # markdown recipe loader
│   ├── agent/                # agent.md loader
│   ├── tool/                 # Tool.define + registry + load_recipe
│   ├── session/              # message, service, LLM stream, loop, compaction
│   ├── bindu/                # Bindu A2A: protocol, identity, auth, client
│   ├── planner/              # agent catalog → dynamic tools + tool-id collision guard
│   ├── server/               # Hono shell + /health
│   ├── api/                  # POST /plan + SSE emitter
│   └── index.ts              # Layer graph + boot
└── tests/                    # unit + integration suites
```

Modules vendored from [sst/opencode](https://github.com/sst/opencode) (MIT-licensed) handle Effect runtime glue and generic utilities (logger, filesystem, ids, XDG paths). Everything else is Bindu-native — written for the gateway, not inherited from OpenCode's coding-tool focus.

---

## License + credits

Apache-2.0.

Effect runtime glue + generic utility modules vendored from [sst/opencode](https://github.com/sst/opencode) at `src/_shared/` and `src/{effect,util,id,global}/`. Coding-specific features (LSP, git, bash/edit tools, IDE integration) were intentionally not carried over — the gateway is a multi-agent orchestrator, not a coding shell.
