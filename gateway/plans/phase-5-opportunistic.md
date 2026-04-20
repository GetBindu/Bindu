# Phase 5 — Opportunistic

**Duration:** no fixed duration; buckets pull independently after Phase 2
**Goal:** Ship individual advanced features as concrete demand arises, not as a monolith.
**Deliverable:** each bucket is independently shippable.

---

## How to use this phase

Do NOT build Phase 5 as one block. Each bucket is its own small project with its own ADR. Pull a bucket only when:
1. A concrete user / customer / integration demands it
2. Phases 1–2 (minimum) have shipped and stabilized
3. You can explain the use case in one sentence to a non-engineer

---

## Buckets

### Bucket A — Payments (x402 REST side channel)

**Use case:** skills that charge per call; commercial agent marketplaces.

**Already real in deployed Bindu specs** — `/api/start-payment-session`, `/api/payment-status/{sessionId}`, `/payment-capture` are present on every deployed Bindu agent we audited. This bucket is "wire it through the gateway", not "design from scratch".

**Tasks**
- Detect payment-required: HTTP 402 response OR task state `payment-required` from peer
- On detection:
  1. `POST {peer}/api/start-payment-session` → receive `{ sessionId, url, expiresAt }`
  2. Emit SSE frame `event: payment_required` to External with `{ url, sessionId, expiresAt, task_id }`
  3. External collects payment out-of-band (user visits `url` → browser paywall)
  4. Gateway long-polls `GET {peer}/api/payment-status/{sessionId}?wait=true` (up to 5 min)
  5. On `status: completed`, re-submit the original `message/send` with `paymentToken` in `message.metadata`
  6. On `status: failed` or timeout, emit `event: payment_failed`; plan surfaces typed error to planner
- AP2 mandate schemas in `bindu/protocol/payments.ts` (`IntentMandate`, `CartMandate`, `PaymentMandate`) — parse permissively from `paymentContext` metadata; pass through, don't construct
- Config: `gateway.bindu.payments.enabled`, `gateway.bindu.payments.maxPerCall`, `gateway.bindu.payments.dailyCap`, `gateway.bindu.payments.poll.maxSeconds`

**Skip until:** a commercial Bindu agent appears in a tenant's agent catalog AND the tenant accepts payment flows. Standalone demo doesn't require this.

---

### Bucket B — Feedback (`tasks/feedback`)

**Use case:** close the loop — rate peer responses, feed trust scoring.

**Tasks**
- `tasks/feedback` method on client; on plan completion, External may POST ratings per task
- Feed `schemaCleanHits` / user rating into Phase 4 trust scorer
- Config: `gateway.bindu.feedback.sendDefault` (off by default)

**Skip until:** Phase 4 trust scores need quality signals beyond schema / signature.

---

### Bucket C — Negotiation-driven routing

**Use case:** planner faces an ambiguous task with N viable peers; pick best via capability match + peer self-assessment.

**`/agent/negotiation` is deployed today** on every Bindu agent we audited. The endpoint returns `{ accepted, score, confidence, rejection_reason?, queue_depth?, subscores? }`. Gateway can probe peers proactively before committing a task.

**Tasks**
- Before calling one of N ambiguous peers: `POST {peer}/agent/negotiation` with:
  ```
  task_summary (the planner's current-task description),
  input_mime_types, output_mime_types,
  max_latency_ms, max_cost_amount,
  required_tools, forbidden_tools,
  min_score, weights
  ```
- Score returned bids; apply `min_score` cutoff; pick top K by `score × confidence`.
- Tie-breaker when client-side AgentCard scoring (Phase 4) is inconclusive.
- Cache negotiation responses with short TTL (30s) to avoid per-turn re-negotiation on identical tasks.
- Bus event `bindu.negotiation.decided { task_summary, winner, losers, scores }` for audit.
- Config: `gateway.bindu.negotiation.enabled`, `gateway.bindu.negotiation.topK`, `gateway.bindu.negotiation.minScore`, `gateway.bindu.negotiation.weights`.
- Blend with Phase 4 trust scoring: final rank = `negotiation_score × trust_score`.

**Skip until:** users complain that planner picks suboptimal peers, OR Phase 4 trust scoring proves insufficient on its own.

---

### Bucket D — Push notifications (`tasks/pushNotification/*`)

**Use case:** very long-running tasks (hours–days) where SSE is impractical.

**Tasks**
- `tasks/pushNotification/set|get` on client — register webhook for task completion
- Gateway callback endpoint `POST /bindu/callbacks/:task_id` with HMAC verification
- External: plan can complete async; External polls `GET /plan/:session_id` or registers own webhook
- Config: `gateway.callbacks.url`, `gateway.callbacks.hmacSecret`

**Skip until:** a real use case with >5-minute tasks appears.

---

### Bucket E — Federated skill marketplace

**Use case:** discover skills, not just agents.

**Tasks**
- `GET {peer}/skills/feed` (Bindu extension) — subscribed peers publish skill updates
- Cache skills across all known peers in `gateway_skill_marketplace`
- Query `GET /admin/skills?tag=research` returns matching skills across peers
- Skill versioning: subscribers notified when `version` bumps

**Skip until:** Phase 4 registry insufficient for skill discovery.

---

### Bucket F — Policy-as-code for `bindu_expose` (Phase 3 dependency)

**Use case:** enterprise tenants with complex access rules that outgrow wildcards.

**Tasks**
- Integrate Open Policy Agent (Rego) or CEL evaluator
- Permission rules → policies: `allow if peer.did matches X and skill in Y and time_of_day in Z`
- Config: `gateway.permissions.engine: "rego" | "cel" | "wildcard"`

**Skip until:** a tenant requests this and wildcards provably insufficient.

---

### Bucket G — Multi-region deployment + distributed breaker state

**Use case:** >1 gateway instance per region; circuit-breaker state shared.

**Tasks**
- Move `Breaker` from in-memory → Redis (or Supabase advisory locks)
- Rate-limit buckets → Redis
- Distributed tracing across instances (Otel-enabled from Phase 2)
- Region-aware peer routing (prefer geographically closer)

**Skip until:** gateway runs on >1 instance.

---

### Bucket H — Web UI for operators

**Use case:** non-engineers inspect plans, tenants, peers, audit logs.

**Tasks**
- React + Vite admin dashboard; Supabase auth
- Plan timeline view: SSE replay of past session
- Peer list with trust scores + toggle (pin, quarantine, delete)
- Audit log viewer with filter
- Metrics panels (Grafana iframe or native)

**Skip until:** explicit operator / ops-team request.

---

## Process per bucket

For every bucket pulled:
1. **1-page ADR** — use case, design, integration points, risks
2. **Scoped feature branch** — one bucket per PR, never bundle
3. **Feature flag** — `gateway.experimental.<bucket>` off by default
4. **Sunset criteria** — if unused in 6 months, remove

---

## Non-goals for Phase 5

- No "do all the things" sprints. Pull one bucket at a time.
- No buckets without a named customer / user today.
- No infrastructure rewrites dressed up as Phase 5.
- No speculative scaling beyond current real-world load.

---

## Exit gate

Each bucket ships as patch (`v0.4.1`, `v0.4.2`, …). No composite exit gate. If buckets aggregate to a coherent major version (significant new capabilities, backward-compat shift), cut `v1.0`.
