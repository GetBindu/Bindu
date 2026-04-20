# Phase 2 — Productionization & Resilience

**Duration:** ~2 calendar weeks
**Goal:** Make Phase 1 safe to point real External traffic at.
**Deliverable:** `v0.2` — reconnect, Realtime replay, RLS multi-tenancy, circuit breakers, rate limits, observability, Docker deploy.

---

## Preconditions

- Phase 1 shipped and tagged `gateway-v0.1`
- Gateway running in staging with real Supabase project
- At least one real External client hitting staging (even a test script)
- Decision on tenancy: how tenants are identified (bearer JWT claim, custom header)
- Grafana (or equivalent) instance available if dashboards are desired

---

## Work breakdown

### Feature 1 — Reconnect via `tasks/resubscribe` (3 days)

**What:** External SSE drops → reconnects with `session_id + last_event_id` → receives missed artifacts + live resumes.

**Tasks**
1. Add `tasks/resubscribe` to `src/bindu/protocol/types.ts` + client.
2. Add `last_event_id` column to `gateway_tasks`. Every emitted SSE frame has monotonic ID.
3. `GET /plan/:session_id/resubscribe?from=<eventId>` — replay stored events + live-tail via Realtime.
4. Supabase Realtime subscription on `gateway_tasks` for the session.
5. Merge stored + live; dedupe by event ID.
6. Tests: drop client mid-plan, reconnect, assert zero loss.

### Feature 2 — Session TTL + cleanup (0.5 day)

**Tasks**
1. `migrations/002_ttl.sql`: function `prune_old_sessions()` deletes `last_active_at < now() - interval '30 days'`.
2. `pg_cron`:
   ```sql
   select cron.schedule('prune-sessions', '0 3 * * *', 'select prune_old_sessions()');
   ```
3. Config `gateway.session.ttl_days` (default 30).
4. Test: insert backdated row, run function, gone.

### Feature 3 — Multi-tenancy + RLS (2 days)

**Tasks**
1. `migrations/003_tenancy.sql`: add `tenant_id TEXT NOT NULL DEFAULT 'default'` to all 3 tables; indexes.
2. Tenant resolver from bearer JWT claim or `X-Tenant-Id` header. Fail-closed if missing.
3. RLS policies gate on `tenant_id = current_setting('request.tenant_id')`. Service role bypasses but policies defend future direct-token paths.
4. Every write sets `tenant_id`.
5. Test: two tenants; A can't read B via non-service-role token.

### Feature 4 — Circuit breaker per peer (1.5 days)

**Tasks**
1. `src/bindu/client/breaker.ts`: in-memory state `CLOSED | OPEN | HALF_OPEN`; `N` failures → OPEN for `M` minutes.
2. Wire into `BinduClient.callPeer`: OPEN → immediate `peer_quarantined` failure, no network hit.
3. Bus event `bindu.peer.quarantined { peer, until }`.
4. Config `gateway.limits.breaker = { failureThreshold: 5, cooldownMs: 120000 }`.
5. Tests: flapping peer → quarantined; next call fails fast; auto-recover after cooldown.

### Feature 5 — Rate limits (1 day)

**Tasks**
1. Token bucket per tenant on `POST /plan` (Hono middleware).
2. Token bucket per peer on outbound Bindu calls.
3. Global inbound QPS cap.
4. Config `gateway.limits.rate = { perTenant: 60/min, perPeer: 30/sec, global: 100/sec }`.
5. 429 with `Retry-After` when hit.
6. Tests: burst N, observe throttle.

### Feature 6 — Observability (2 days)

**Tasks**
1. **OpenTelemetry**
   - `bun add @opentelemetry/api @opentelemetry/sdk-node @opentelemetry/exporter-trace-otlp-http`
   - Spans wrap `POST /plan`, each `Bindu.callPeer`, each DB call.
   - Single `trace_id` → `Message.metadata.trace_id` so peers continue the trace.
2. **Structured audit log**
   - Config `gateway.audit.enabled: true`, `gateway.audit.sink: "file" | "table"`
   - File: JSONL append to `$LOG_DIR/audit.log`
   - Table: `gateway_audit_log` — `{ tenant_id, direction, session_id, peer, payload_hash, status, ts }`
   - Payloads hashed (sha256) by default; opt-in raw via `gateway.audit.include_payloads: true`
3. **Prometheus `/metrics`**
   - `gateway_plan_duration_seconds` histogram
   - `gateway_bindu_calls_total{peer, state}` counter
   - `gateway_db_errors_total{op}` counter
   - `gateway_active_sessions` gauge
4. Grafana dashboard JSON in `gateway/dashboards/overview.json`.

### Feature 7 — Docker + deploy recipe (1 day)

**Tasks**
1. `gateway/Dockerfile` — multi-stage Bun build, slim runtime.
2. `gateway/docker-compose.yml` — gateway + 2 mock agents + optional local Supabase stack.
3. `gateway/deploy/{fly.toml,render.yaml,railway.json}`.
4. README: env vars, ports, health check, rollout.
5. `docker-compose up` works end-to-end with demo request.

---

## Code sketches

### Circuit breaker — `src/bindu/client/breaker.ts`

```ts
type State = "CLOSED" | "OPEN" | "HALF_OPEN"
interface PeerState { state: State; failures: number; openedAt: number | null }

export class Breaker {
  private peers = new Map<string, PeerState>()
  constructor(private threshold = 5, private cooldownMs = 120_000) {}

  canCall(key: string): boolean {
    const p = this.peers.get(key) ?? { state: "CLOSED", failures: 0, openedAt: null }
    if (p.state === "OPEN" && p.openedAt && Date.now() - p.openedAt > this.cooldownMs) {
      this.peers.set(key, { ...p, state: "HALF_OPEN" })
      return true
    }
    return p.state !== "OPEN"
  }

  onSuccess(key: string) {
    this.peers.set(key, { state: "CLOSED", failures: 0, openedAt: null })
  }

  onFailure(key: string): { quarantined: boolean; until?: number } {
    const p = this.peers.get(key) ?? { state: "CLOSED", failures: 0, openedAt: null }
    const failures = p.failures + 1
    if (failures >= this.threshold) {
      const openedAt = Date.now()
      this.peers.set(key, { state: "OPEN", failures, openedAt })
      return { quarantined: true, until: openedAt + this.cooldownMs }
    }
    this.peers.set(key, { ...p, failures })
    return { quarantined: false }
  }
}
```

### RLS — `migrations/003_tenancy.sql`

```sql
alter table gateway_sessions add column if not exists tenant_id text not null default 'default';
alter table gateway_messages add column if not exists tenant_id text not null default 'default';
alter table gateway_tasks    add column if not exists tenant_id text not null default 'default';

create index on gateway_sessions (tenant_id, last_active_at);
create index on gateway_messages (tenant_id, session_id);
create index on gateway_tasks    (tenant_id, session_id);

drop policy if exists tenant_isolation on gateway_sessions;
create policy tenant_isolation on gateway_sessions
  for all
  using (tenant_id = current_setting('request.tenant_id', true))
  with check (tenant_id = current_setting('request.tenant_id', true));
-- Same for messages and tasks
```

### Rate limit middleware — `src/api/rate-limit.ts`

```ts
import { MiddlewareHandler } from "hono"

interface Bucket { tokens: number; refilledAt: number }
const buckets = new Map<string, Bucket>()

export const rateLimit = (limit: number, windowMs: number): MiddlewareHandler =>
  async (c, next) => {
    const key = c.get("tenantId") ?? "anon"
    const b = buckets.get(key) ?? { tokens: limit, refilledAt: Date.now() }
    const now = Date.now()
    const refill = Math.floor(((now - b.refilledAt) / windowMs) * limit)
    b.tokens = Math.min(limit, b.tokens + refill)
    b.refilledAt = now

    if (b.tokens <= 0) {
      c.header("Retry-After", String(Math.ceil(windowMs / 1000)))
      return c.json({ error: "rate_limited" }, 429)
    }
    b.tokens -= 1
    buckets.set(key, b)
    await next()
  }
```

---

## Test plan

**Unit tests (new)**
- `bindu/client/breaker.test.ts` — transitions; cooldown expiry; HALF_OPEN probe
- `api/rate-limit.test.ts` — burst, throttle, refill over time
- `db/tenancy.test.ts` — RLS: tenant A ≠ tenant B (non-service-role JWT)
- `observability/audit.test.ts` — payload hashing; JSONL + DB sinks

**Integration tests (new)**
- `tests/integration/resubscribe.test.ts` — drop client at frame 3/10, reconnect, receive 4–10 + done
- `tests/integration/circuit-breaker.test.ts` — failing peer → quarantine → recover
- `tests/integration/tenants.test.ts` — concurrent tenants, zero cross-contamination
- `tests/integration/ttl-prune.test.ts` — backdated session, run prune, gone

**Manual**
- Deploy to staging via `docker-compose up`
- 100 concurrent `/plan` requests; Grafana shows healthy metrics
- Kill Supabase mid-plan → graceful error, recovers on reconnect

---

## Phase-specific risks

| Risk | Severity | Mitigation |
|---|---|---|
| Realtime latency inflates E2E time | MEDIUM | Benchmark first; fall back to polling `gateway_tasks` if p99 > 500ms |
| RLS false-positives block legit traffic | HIGH | All tests include non-service-role path; 48h staging soak |
| Breaker state not shared across instances | MEDIUM | Per-instance in-memory OK for Phase 2; Phase 4 moves to Redis |
| Audit log PII leakage | HIGH | Default: payload-hash-only; raw opt-in + prompt |
| OTel overhead | LOW | 10% sampling default; 100% in staging |
| Dashboard drift | LOW | Version dashboard JSON; re-import per release |

---

## Exit gate

1. External drops SSE mid-plan → reconnects via replay endpoint → no loss
2. Tenant A can't see tenant B's sessions (integration test)
3. Flapping peer quarantined; fails fast until cooldown; auto-recovers
4. Grafana shows live traffic, errors, p95 duration
5. `docker-compose up` → gateway + local Supabase + 2 mock agents + Grafana
6. All Phase 1 tests still green

→ Ship `v0.2`.
