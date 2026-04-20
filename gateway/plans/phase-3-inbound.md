# Phase 3 — Inbound Exposure (OPTIONAL)

**Duration:** ~2 calendar weeks (only if needed)
**Goal:** Make the gateway itself a **callable Bindu agent** — peers `POST /bindu/gateway/` with JSON-RPC and get a streamed plan result.
**Deliverable:** `v0.3` — inbound server, DID signing, OAuth2/mTLS inbound validation, `.well-known/agent.json`, `/did/resolve`.

---

## When to do this phase

**Skip if:** architecture stays External → Gateway → Agents forever. Nothing in the stated product requires the gateway to be *callable*.

**Do this if:**
- Another service / peer Bindu agent wants to invoke the gateway's planner as a skill
- You want to federate: the gateway appears in another gateway's agent catalog
- You need async results via `tasks/pushNotification` (Phase 5 precursor)

---

## Preconditions

- Phase 2 shipped, stable in production ≥1 week
- Explicit business requirement, documented in an issue
- mTLS CA available (step-ca / Vault / managed) OR start OAuth-only
- DNS + TLS cert for inbound endpoint

---

## Work breakdown

### Feature 1 — Inbound routes + dispatch (3 days)

**Tasks**
1. `src/bindu/server/index.ts` — Hono router at `/bindu/:agent/`.
2. `src/bindu/server/jsonrpc.ts` — JSON-RPC 2.0 decoder + dispatcher by `method`.
3. `src/bindu/server/handlers/message-send.ts` — validate, auth, DID-verify, create task, return `{ state: submitted }`; kick off background SessionPrompt.
4. `src/bindu/server/handlers/message-stream.ts` — same + hold SSE, stream artifacts.
5. `src/bindu/server/handlers/tasks-*.ts` — `get`, `cancel`, `list`.
6. `src/bindu/server/bridge.ts` — Bindu Message ↔ SessionPrompt.PromptInput; parts + events → Artifacts/TaskStatus.
7. Per-agent `bindu.expose: true` in agent `.md` frontmatter.
8. Exposed agents get a route; 404 otherwise.

### Feature 2 — DID signing (outbound, 2 days)

**Tasks**
1. `src/bindu/identity/sign.ts` — add `sign(text, privateKey)` function. Previously verify-only.
2. Keystore for gateway's own DID:
   - Generate at first run: `bun scripts/did-keygen.ts` → `auth.json` as `DIDAuth`
   - Config `gateway.expose.did = { method: "bindu" | "key", author?: string }`
3. Every outbound Artifact text part signed.
4. `.well-known/agent.json` — `src/bindu/server/well-known.ts` advertises DID + skills + security schemes.
5. `POST /did/resolve` — returns the gateway's DID Document.
6. Tests: keypair → DID → self-verify; sign → base58 sig → verify.

### Feature 3 — Inbound authentication (2 days)

**Tasks**
1. `src/bindu/server/auth/oauth-verifier.ts` — `Authorization: Bearer` against configured issuer (Hydra introspection or local JWKS).
2. `src/bindu/server/auth/did-verifier.ts` — verify `message.parts[].metadata["did.message.signature"]` against peer's DID Doc (cached).
3. Layered policy: peer config declares what's required (OAuth only, DID only, both).
4. Config `gateway.expose.auth = { oauth?: { issuer, jwks }, didRequired?: boolean }`.
5. Failure modes: `-32009`, `-32010/11/12`, `-32013`, `-32006`.
6. Tests: 4 combos (oauth-yes/no × did-yes/no).

### Feature 4 — mTLS server + client (1.5 days)

**Tasks**
1. Server: `Bun.serve({ tls: { cert, key, ca } })` + require client cert.
2. Client: per-peer `https.Agent({ cert, key, ca })` wired into `src/bindu/client/fetch.ts` when `MTLSAuth`.
3. Cert-pinning option per peer (`trust.pinnedCertSha`).
4. Config: `MTLSAuth` variant. Cert/key/ca paths.
5. Tests: step-ca cert → accepted; self-signed without pin → rejected.

### Feature 5 — Inbound permissions (`bindu_expose`) (1 day)

**Tasks**
1. New permission key `bindu_expose` — patterns match peer DIDs.
2. Inbound session ruleset: `agent.permission` minus admin tools.
3. `trustedPeers[DID].autoApprove` whitelists per peer.
4. Untrusted DID → `-32013`.

### Feature 6 — Admin + operational glue (1 day)

**Tasks**
1. Add `bindu.expose.*` to existing metrics / audit.
2. CLI:
   - `bindu-gateway did keygen`
   - `bindu-gateway did rotate` (old key grace period)
   - `bindu-gateway bindu peers`
3. README: how to expose an agent; DID lifecycle; cert lifecycle.

---

## Code sketches

### `src/bindu/server/handlers/message-stream.ts`

```ts
import { streamSSE } from "hono/streaming"
import { Effect, Stream } from "effect"
import { SessionPrompt } from "../../../session/prompt"
import { binduToPromptInput, partToArtifact } from "../bridge"
import { sign } from "../../identity/sign"

export const messageStreamHandler = async (c) => {
  const req = jsonRpcRequestSchema.parse(await c.req.json())
  const { message } = req.params

  await verifyAuth(c, message)                       // OAuth + DID verify
  const agentName = c.req.param("agent")
  const input = binduToPromptInput(message, agentName)

  return streamSSE(c, async (stream) => {
    // First frame: Task { state: submitted }
    await stream.writeSSE({
      data: JSON.stringify({
        jsonrpc: "2.0",
        id: req.id,
        result: {
          kind: "task",
          id: input.taskId,
          contextId: input.contextId,
          status: { state: "submitted", timestamp: new Date().toISOString() },
        },
      }),
    })

    const events = await Effect.runPromise(SessionPrompt.prompt(input))

    await Effect.runPromise(
      Stream.runForEach(events, (event) => Effect.promise(async () => {
        if (event._tag === "Part") {
          const art = partToArtifact(event, input.taskId)
          for (const part of art.parts ?? []) {
            if (part.kind === "text") {
              part.metadata = {
                ...(part.metadata ?? {}),
                "did.message.signature": await sign(part.text),
              }
            }
          }
          await stream.writeSSE({
            data: JSON.stringify({
              jsonrpc: "2.0",
              id: req.id,
              result: { kind: "artifact-update", artifact: art },
            }),
          })
        }
        if (event._tag === "Status") {
          await stream.writeSSE({
            data: JSON.stringify({
              jsonrpc: "2.0",
              id: req.id,
              result: { kind: "status-update", status: event.status },
            }),
          })
        }
      }))
    )
  })
}
```

### `src/bindu/identity/sign.ts` — extended

```ts
import * as ed25519 from "@noble/ed25519"
import bs58 from "bs58"
import { Effect } from "effect"
import { Auth } from "../../auth"

export const sign = (text: string) => Effect.gen(function* () {
  const auth = yield* Auth.Service
  const did = yield* auth.get("gateway.self.did")
  if (did?.type !== "did") return yield* Effect.fail(new Error("no DIDAuth configured"))

  const privateBytes = bs58.decode(did.privateKeyBase58)
  const msgBytes = new TextEncoder().encode(text)
  const sig = await ed25519.sign(msgBytes, privateBytes)
  return bs58.encode(sig)
})
```

### `migrations/004_inbound.sql`

```sql
alter table gateway_tasks add column if not exists direction text not null default 'outbound'
  check (direction in ('outbound', 'inbound'));
create index on gateway_tasks (tenant_id, direction, started_at);

create table if not exists gateway_trusted_peers (
  did               text primary key,
  tenant_id         text not null default 'default',
  pinned_cert_sha   text,
  auto_approve      text[] not null default '{}',
  added_at          timestamptz not null default now(),
  last_seen_at      timestamptz
);
alter table gateway_trusted_peers enable row level security;
```

---

## Test plan

**Unit tests (new)**
- `bindu/server/jsonrpc.test.ts` — malformed → correct error codes
- `bindu/identity/sign.test.ts` — sign/verify round-trip
- `bindu/server/auth/oauth-verifier.test.ts` — valid, expired, bad sig, missing scopes
- `bindu/server/auth/did-verifier.test.ts` — valid sig, tampered text, wrong pubkey
- `bindu/server/bridge.test.ts` — Bindu ↔ PromptInput round-trip

**Integration tests**
- `tests/integration/inbound-message-stream.test.ts` — peer sends `message/stream`; gateway streams artifacts; peer verifies sigs
- `tests/integration/inbound-unauthorized.test.ts` — peer without DID or wrong OAuth → `-32013`
- `tests/integration/mtls-handshake.test.ts` — step-ca cert OK; self-signed rejected
- `tests/integration/well-known.test.ts` — `GET /.well-known/agent.json` valid; `POST /did/resolve` valid

**Conformance**
- Python Bindu reference agent calls our inbound endpoint
- AgentCard schema validates against Bindu's Pydantic model

---

## Phase-specific risks

| Risk | Severity | Mitigation |
|---|---|---|
| DID format drift — emit unparseable DIDs | HIGH | Conformance vs Python reference; fuzz `did:bindu:` format |
| Signature over wrong bytes | HIGH | Bindu signs raw UTF-8 of `part.text`; `sign()` mirrors exactly |
| mTLS key/cert management complexity | MEDIUM | Document step-ca setup verbatim; `bunx cert-bootstrap` script |
| Inbound DoS amplification | HIGH | Phase 2 limits apply; inbound-specific max concurrent tasks |
| Permission escalation via inbound | MEDIUM | Stripped ruleset (no bash/edit); `allowEgress: false` default |
| OAuth token replay | MEDIUM | `nbf`/`exp` 5-min window; track JTI (stretch) |
| PII in inbound messages logged | MEDIUM | Audit hashes; raw opt-in |

---

## Exit gate

1. Peer Bindu agent calls `POST /bindu/gateway/` `message/stream` → streamed plan result
2. Outbound artifacts carry valid `did.message.signature`; peer verifies
3. Pinned DID enforcement: untrusted → `-32013`
4. mTLS with step-ca cert succeeds; self-signed rejected
5. All Phase 1 + 2 tests still green

→ Ship `v0.3`.
