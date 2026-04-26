---
id: 2026-04-18-compaction-concurrent-races
title: Concurrent /plan requests on same session ran compaction twice, racing on the summary
severity: high
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: gateway/session
commit: 0655ac1
---

## Symptom

Two `/plan` requests arriving for the same `session_id` within a few
hundred milliseconds both triggered compaction. Three observable
effects:

1. **Double LLM cost.** Both requests summarized the same history into
   a paragraph. Each paid for an Anthropic/OpenAI call.
2. **Silent fact loss.** LLMs are non-deterministic even at
   `temperature: 0.2`. The two summaries diverged in *which* facts they
   preserved. The second `UPDATE` to `gateway_sessions.compaction_summary`
   overwrote the first. If the winning paragraph happened to omit facts
   the losing paragraph captured, those facts were gone.
3. **Non-reproducibility.** Replaying identical inputs 5 seconds later
   could produce a different session state, because which compaction
   "won" depended on sub-millisecond timing.

The second effect is the data-loss path. The first is a cost issue.
The third makes the whole thing hard to reason about after the fact.

## Root cause

No serialization anywhere in the compaction path. `compactIfNeeded` was
a pure Effect — called directly from the planner's `runPlan`, no lock,
no mutex, no dedupe map. Concurrent invocations interleaved:

```
T=0ms    A: history = sessions.history(sessionID)          # 40 rows
T=1ms    B: history = sessions.history(sessionID)          # same 40 rows
T=2ms    A: read compaction_summary = null
T=3ms    B: read compaction_summary = null
T=10ms   A: summarize(head, priorSummary=null) → "Summary A..."
T=12ms   B: summarize(head, priorSummary=null) → "Summary B..."
T=800ms  A: UPDATE gateway_messages SET compacted=true WHERE id IN (1..36)
T=801ms  B: UPDATE gateway_messages SET compacted=true WHERE id IN (1..36)   # idempotent
T=802ms  A: UPDATE gateway_sessions SET compaction_summary = "Summary A"
T=803ms  B: UPDATE gateway_sessions SET compaction_summary = "Summary B"     # wins
```

Mental model: "each request is a pure function of its inputs; if two
requests compute the same thing, they'll converge." True for
deterministic computations. False for LLM calls — compaction is a
stochastic transform of the history, and running it twice produces
two different valid answers.

The head-row UPDATE (`SET compacted=true`) is idempotent so that part
was harmless. The summary-column UPDATE was the unsafe operation, and
it had no concurrency control.

## Fix

Application-layer promise dedupe in the compaction layer
(`gateway/src/session/compaction.ts`):

```ts
const inflight = new Map<SessionID, Promise<CompactOutcome>>()

function dedupe(sessionID, producer) {
  const existing = inflight.get(sessionID)
  if (existing) return existing                          // reuse, don't run
  const p = producer().finally(() => {
    if (inflight.get(sessionID) === p) inflight.delete(sessionID)
  })
  inflight.set(sessionID, p)
  return p
}
```

Second caller for a session finds the existing in-flight promise and
awaits it — receives the SAME `CompactOutcome` as the first caller.
Only one LLM call. Only one set of UPDATEs. No race.

The entry is cleared in a `finally` so a resolved (or failed)
compaction does not block subsequent ones. On rejection, the next
caller starts a fresh producer, enabling retry.

Regression tests at `gateway/tests/session/compaction-dedupe.test.ts`:
four cases covering reuse of in-flight promise, post-settle re-entry,
per-session isolation (different keys don't collide), and
error-path recovery.

**Known limitation documented in the commit and code comment:** this
is per-process state. A horizontally-scaled deployment of the gateway
(multiple processes fronting one Supabase) could still race across
processes. Single-process Phase 1 is correct today; Phase 2 should
add either a Postgres version column with optimistic concurrency or
a wrap-everything-in-a-stored-procedure approach. Tracked in
`known-issues.md` under `compaction-dedupe-single-process-only`.

## Why the tests didn't catch it

No concurrency tests existed in the session layer. Compaction was
untested end-to-end (separate issue — see
`2026-04-18-compaction-lossy-second-pass.md` and
`2026-04-18-compaction-mid-turn-cut.md`, which share the root cause
of "compaction had no test harness").

Even with a proper compaction harness, this specific bug requires
**concurrent** invocation to manifest. Vitest tests are sequential by
default; you have to explicitly construct `Promise.all([call(), call()])`
to reproduce the race. That's the kind of test you write only after
you already know concurrency is a failure mode.

The regression test for this fix is itself instructive: it tests the
dedupe *wrapper* (a pure function) rather than the full compaction
path, because mocking Supabase + the LLM together is expensive. The
wrapper's properties (reuse, clear-on-settle, key isolation,
error recovery) are what actually prevent the race; if those hold,
the application of the wrapper to compaction is trivial.

## Class of bug — where else to watch

**"Non-idempotent operation on a shared row"** — any database write
that replaces state based on read-then-compute must either serialize
across concurrent writers or use compare-and-swap semantics. Ask for
each write path: "if two requests did this concurrently, would the
outcome depend on timing?"

Specific candidates in the codebase:

- `db.updateSessionCatalog` wholesale-overwrites the
  `agent_catalog` column on every `/plan`. Two concurrent requests
  for the same session could race on which catalog version wins.
  If catalogs differ (different tenants, different external configs),
  the losing one's agents are silently dropped. Noted in
  `known-issues.md` under `agent-catalog-overwrite` and
  `agent-catalog-race`.
- `db.touchSession` does an `UPDATE ... SET last_active_at = now()`.
  Idempotent, safe — this is the right shape.
- Any future payment-state updates (`x402` processing in Phase 5)
  will need concurrency control by definition. If using Postgres,
  prefer `SELECT ... FOR UPDATE` or advisory locks; if using
  application-level, the dedupe pattern here generalizes.
- The `gateway_tasks.state` column is updated by `finishTask`. Single
  writer per task id, so safe today. If a future feature lets the
  gateway retry a task (re-finishing it with a different outcome),
  serialization becomes necessary.

**Secondary rule of thumb: in-process dedupe is cheap and correct for
single-process deployments. Cross-process is a different problem; plan
for it before scaling horizontally, don't discover it during.**
