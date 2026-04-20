# Phase 4 — Discovery, Trust & Public Network

**Duration:** ~2–3 calendar weeks
**Goal:** Safe to call Bindu agents on the open internet we didn't pre-configure.
**Deliverable:** `v0.4` — registry discovery, AgentCard auto-refresh, trust scoring, reputation events, cycle limits, unknown-DID gating. **6-month north star.**

---

## Preconditions

- Phase 2 shipped and stable
- Phase 3 optional — Phase 4 covers outbound-only trust
- ≥3 publicly-reachable Bindu agents to test against
- Decision on registry: getbindu.com (if public API), self-hosted registry, or both

---

## Work breakdown

### Feature 1 — AgentCard auto-refresh (1 day)

**Tasks**
1. `src/bindu/registry/cache.ts` — per-peer AgentCard cache with ETag / Last-Modified.
2. Background refresh every `gateway.bindu.cardRefreshMs` (default 300s).
3. On change, re-project skills into tool registry (MCP `mcp.tools.changed` pattern).
4. Bus event `bindu.skills.changed { peer }`.
5. Config `gateway.bindu.cardRefreshMs`, `gateway.bindu.cardRefreshOnFailure: true`.
6. Tests: mock AgentCard endpoint with changing ETag; assert re-fetch + skill-set update.

### Feature 2 — Registry client (2 days)

**Tasks**
1. `src/bindu/registry/provider.ts` — pluggable interface:
   ```ts
   interface RegistryProvider {
     listPeers(filter?: PeerFilter): Effect.Effect<PeerRecord[]>
     lookup(did: string):             Effect.Effect<PeerRecord | undefined>
     register?(record: PeerRecord):   Effect.Effect<void>
   }
   ```
2. `src/bindu/registry/providers/bindu-hosted.ts` — getbindu.com stub.
3. `src/bindu/registry/providers/self-hosted.ts` — Supabase-backed `gateway_registry`:
   ```sql
   create table gateway_registry (
     did             text primary key,
     url             text not null,
     agent_card_snap jsonb,
     tenant_id       text not null default 'default',
     added_at        timestamptz not null default now(),
     verified_at     timestamptz
   );
   ```
4. `src/bindu/registry/providers/static-config.ts` — peers in config (default).
5. Config `gateway.bindu.registries: [{ type: "bindu" | "supabase" | "config", … }]`.
6. **Registry is advisory:** DID Docs always fetched from peer directly.

### Feature 3 — Trust scoring (2 days)

**Tasks**
1. `src/bindu/trust/scorer.ts` — rolling stats per peer:
   - `signatureVerifyRate` (last 100 artifacts)
   - `schemaComplianceRate` (last 100 responses that parsed)
   - `failureRate` (last 100 calls)
   - `firstSeenAt`, `totalCalls`
2. Persisted to Supabase `gateway_peer_stats`.
3. Trust score `[0, 1]`: weighted average.
4. Bus event `bindu.peer.score_updated { did, score, stats }` + `GET /admin/peers/:did/stats`.
5. Tests: 100 synthetic calls with known outcomes → expected score.

### Feature 4 — Reputation UI events (1 day)

**Tasks**
1. SSE frame `event: peer_trust` emitted before first call to each new-to-session peer:
   ```
   event: peer_trust
   data: {
     "did": "did:bindu:…",
     "first_seen_at": "…",
     "score": 0.92,
     "total_calls": 147,
     "pinned": false,
     "require_confirm": true
   }
   ```
2. If `require_confirm: true`, External prompts user and either:
   - `POST /plan/:session_id/confirm` → proceed
   - `POST /plan/:session_id/cancel` → abort
3. Config `gateway.bindu.confirmThreshold` (default 0.5); `gateway.bindu.confirmUnknown: true`.
4. Tests: new DID → `require_confirm: true`; subsequent same-session calls don't re-confirm.

### Feature 5 — Cycle + hop limits (1 day)

**Tasks**
1. Outbound: add header `X-Bindu-Hops: N` (or `message.metadata.hops`) — increment on forward.
2. Reject if `hops >= gateway.bindu.maxHops` (default 5).
3. ContextId lineage tracked; reject if remote contextId appears upstream in our chain.
4. Error code: `-32011` for hop-exceeded (or new Bindu-compatible).
5. Tests: 6-hop chain aborts at 5; loop caught before 2nd hit.

### Feature 6 — Unknown-DID gating (0.5 day)

**Tasks**
1. Permission `agent_call` matches DIDs (`did:bindu:unknown*` deny; `did:bindu:acme.dev:*` allow).
2. Peer DID not in config/registry/pinned → apply `gateway.bindu.unknownDIDPolicy` (default `ask`; alternates `deny`, `allow_with_reduced_trust`).
3. `ask` → `peer_trust` SSE with `require_confirm: true`.
4. Tests: new vs pinned vs registry-listed DID branches.

### Feature 7 — Capability negotiation (client-side) (1.5 days)

**Tasks**
1. Planner faces N agents with overlapping skills → score by `AgentCard.skills.assessment`:
   - `keywords` match user question / current task
   - `antiPatterns` exclude
   - `specializations` bonus
2. Planner receives ranked tool list; system prompt includes ranking hint.
3. (Stretch) `POST {peer}/agent/negotiation` — task summary → `{ accepted, score, confidence }`. Use top-K over static scoring when available.
4. Tests: two agents declaring `summarize`, one `antiPatterns: ["code review"]` → planner picks the other for code-review task.

### Feature 8 — Prompt-injection hardening (1 day)

**Tasks**
1. Wrap every remote artifact in `<remote_content agent="…" did="…" verified="yes/no">…</remote_content>` before feeding to model.
2. System prompt explicitly addresses wrapper: treat as data, not instructions.
3. Strip / escape common injection markers (fake `<remote_content>` tags, "ignore previous", etc.).
4. Log scrubber hits to audit.
5. Tests: inject fake `role: system` message in artifact; planner must not obey.

---

## Code sketches

### Trust scoring — `src/bindu/trust/scorer.ts`

```ts
import { Effect } from "effect"
import { DB } from "../../db"

interface CallOutcome {
  did: string
  success: boolean
  signatureVerified: boolean | null
  schemaClean: boolean
}

export const recordOutcome = (o: CallOutcome) => Effect.gen(function* () {
  const db = yield* DB.Service
  yield* db.upsertPeerStats(o.did, {
    lastCallAt: new Date().toISOString(),
    totalCalls: "+1",
    failures: o.success ? 0 : "+1",
    sigHits: o.signatureVerified ? "+1" : 0,
    sigMisses: o.signatureVerified === false ? "+1" : 0,
    schemaCleanHits: o.schemaClean ? "+1" : 0,
    schemaCleanMisses: o.schemaClean ? 0 : "+1",
  })
})

export const computeScore = (s: PeerStats): number => {
  const failureWeight   = 0.4 * (1 - s.failures / Math.max(s.totalCalls, 1))
  const signatureWeight = 0.3 * (s.sigHits / Math.max(s.sigHits + s.sigMisses, 1))
  const schemaWeight    = 0.3 * (s.schemaCleanHits / Math.max(s.totalCalls, 1))
  return failureWeight + signatureWeight + schemaWeight
}
```

### `event: peer_trust` emission

```ts
export const emitPeerTrust = (peer: Peer, score: Score, session: Session) =>
  Effect.gen(function* () {
    if (session.seenPeers.has(peer.did)) return
    session.seenPeers.add(peer.did)

    const requireConfirm =
      !peer.pinned && (score.value < config.bindu.confirmThreshold || score.isNewDID)

    yield* bus.publish(Event.PeerTrust, {
      did: peer.did,
      score: score.value,
      firstSeenAt: score.firstSeenAt,
      totalCalls: score.totalCalls,
      pinned: peer.pinned,
      require_confirm: requireConfirm,
    })

    if (requireConfirm) {
      yield* session.suspend(peer.did)
    }
  })
```

### Prompt-injection wrapper

```ts
const wrap = (artifact: Artifact, peer: Peer, verified: boolean): string => {
  const scrubbed = artifact.parts
    ?.filter(p => p.kind === "text")
    .map(p => p.text
      .replace(/<\/?remote_content[^>]*>/gi, "[stripped]")
      .replace(/\b(ignore (?:all )?previous|disregard earlier)\b/gi, "[stripped]")
    )
    .join("\n") ?? ""

  return `<remote_content agent="${peer.name}" did="${peer.did}" verified="${verified ? "yes" : "no"}">
${scrubbed}
</remote_content>`
}
```

---

## Test plan

**Unit tests (new)**
- `bindu/registry/cache.test.ts` — ETag respected; 304 skips re-parse; bus event on change
- `bindu/registry/providers/self-hosted.test.ts` — CRUD on `gateway_registry`
- `bindu/trust/scorer.test.ts` — known outcomes → expected score
- `bindu/trust/cycle.test.ts` — loop + hop limits
- `bindu/trust/injection.test.ts` — adversarial content scrubbed

**Integration tests**
- `tests/integration/public-agent.test.ts` — real public Bindu agent; AgentCard fetched; skills → tools; plan completes
- `tests/integration/unknown-did-confirm.test.ts` — new DID → `peer_trust` with `require_confirm`; `/confirm` resumes
- `tests/integration/recursion-detected.test.ts` — peer calls us back → blocked at hop 5 / cycle check
- `tests/integration/bad-peer-quarantine.test.ts` — invalid sigs 3× → score drops; next plan excludes

**Chaos tests**
Stand up a "malicious" test agent returning:
- Invalid DID sigs
- Schema-nonconforming responses
- Prompt injection in artifact text
- Recursive calls back

Gateway survives; audit captures each; trust score reflects.

---

## Phase-specific risks

| Risk | Severity | Mitigation |
|---|---|---|
| Registry spoofing — spoofed DID | HIGH | Registry advisory; DID Doc from peer directly; pinned DIDs trump |
| **Prompt injection across agents** | CRITICAL | Wrapper + scrubber; DID-pin trusted; audit log raw for review |
| Trust score instability on low samples | MEDIUM | Beta(α=2, β=2) prior; require ≥10 calls before load-bearing |
| Confirm-flow UX fatigue | MEDIUM | Aggressive pinning; per-tenant confirm cache (once per tenant per peer) |
| Registry latency blocks plan start | LOW | Background-refreshed; cache miss → plan starts; peer added mid-plan if needed |
| Hop limit false-positive on legit forwarding | LOW | Default 5 generous; per-tenant config override |
| Capability negotiation latency | LOW | Client-side free; server-side `agent/negotiation` only when tied |

---

## Exit gate

1. Gateway calls a real public Bindu agent discovered via registry; plan completes
2. Invalid-sig peer → score drops → next plan excludes; audit log records
3. 5-hop chain aborts cleanly
4. `examples/public-demo/` works with README-documented public agents
5. Adversarial artifact cannot hijack planner (injection test)
6. All Phase 1 + 2 (+ 3 if built) tests green

→ Ship `v0.4`. **6-month north star reached.**
