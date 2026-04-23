---
id: 2026-04-23-poll-budget-unbounded-wall-clock
title: Unbounded poll wall-clock could stall a /plan for hours per tool call
severity: high
status: fixed
found: 2026-04-20
fixed: 2026-04-23
area: gateway/bindu-client
---

## Symptom

A `/plan` request that hit a stuck Bindu peer (returning `working` forever)
would park the whole plan for **up to five minutes per tool call**. The
caller's SSE stream stayed open, the session row stayed locked, and a
client disconnect did not stop the in-flight poll — the gateway kept
hammering the hung peer until the 60-attempt budget was exhausted.

In practice this meant:

- A single misbehaving peer could burn ~5 min of gateway + peer compute
  per call, with nothing the caller could do to reclaim it.
- Aborted requests (user closed the tab, SSE client timed out) still
  consumed backend resources for minutes after the user was gone.
- Legitimate long-running research workloads had no way to express an
  explicit time budget — the only knob was `maxPolls`, which is poorly
  aligned with wall-clock intent.

## Root cause

Two independent gaps:

1. **`sendAndPoll` (`gateway/src/bindu/client/poll.ts`) ignored the abort
   signal between polls.** The loop only checked `maxPolls`; the
   inter-poll `sleep()` was a plain `setTimeout` with no abort wiring.
   Even when the caller's `AbortSignal` fired mid-backoff, the loop kept
   sleeping to the next boundary — up to 10 seconds per iteration.

2. **No plan-level deadline existed.** `PlanPreferences.timeout_ms` was
   declared in the Zod schema but never read by `runPlan`. The planner
   only received `opts?.abort` (the client-disconnect signal from the SSE
   handler), which by itself couldn't express "fail after N seconds."

The combination meant a stuck peer + a silent client = an indefinite
gateway stall, with no API-surfaced way for a caller to cap the blast
radius.

## Fix

Two matching changes, same mental model at both layers:

- **`sendAndPoll` is now abort-aware.** A merged `AbortController`
  composes the caller's signal with an optional `deadlineMs` timer.
  `sleep()` is replaced with `abortableSleep(ms, signal)` that rejects
  immediately on abort. On any abort the client issues a best-effort
  `tasks/cancel` to the peer, then throws
  `BinduError(-32040, AbortedByCaller)` with `data.reason` set to
  `"signal"` or `"deadline"` — callers (and dashboards) can distinguish
  client-disconnect from budget-exceeded without parsing messages.

- **`runPlan` enforces a plan-level deadline.** `preferences.timeout_ms`
  now drives a single `AbortController` at the planner level, forwarded
  into compaction + the prompt loop. Default: **30 min** when unset;
  hard ceiling **6 h** (schema-validated, requests above cap return 400
  at the API boundary). When the deadline fires, the same abort flows
  through `ctx.abort → callPeer({signal}) → sendAndPoll`, cancelling
  every in-flight peer poll simultaneously.

## Why this also fixed `abort-signal-not-propagated-to-bindu-client`

The sibling "medium" bug (client disconnect doesn't cancel in-flight
polls) had the same root cause — `sendAndPoll`'s non-abortable sleep.
The abort-aware rewrite solves both.

## Contract for callers

```json
POST /plan
{
  "question": "…",
  "agents": [...],
  "preferences": { "timeout_ms": 3600000 }  // 1 hour research budget
}
```

- Omit `timeout_ms` → 30 min default.
- Set up to `21_600_000` ms (6 h) for long research plans.
- Above 6 h → `400 invalid_request`. Escalate if you genuinely need more.
- On expiry → `BinduError(-32040, AbortedByCaller)` with
  `data.reason = "deadline"`.

## Tests

- `gateway/tests/bindu/poll.test.ts`: signal abort mid-backoff wakes
  within 500 ms (not 10 s), issues `tasks/cancel` to the peer, throws
  with `reason=signal`. Deadline expiry path mirrors the signal path
  with `reason=deadline`.
- `gateway/tests/integration/bindu-client-e2e.test.ts`: live in-process
  mock agent configured with `stuck: true` verifies the same behavior
  against a real HTTP round-trip.
- `gateway/tests/planner/plan-request-schema.test.ts`: ceiling + floor
  guards for `timeout_ms`.

## Lessons

- **Every wait loop needs an abort-aware sleep.** A signal is only as
  strong as the awaitable that watches it — `setTimeout` is not one of
  those by default. This is the second time in a quarter we've shipped
  a loop that honored signals at the RPC layer but not at the
  back-off boundary; next time, treat the `sleep()` helper as a smell.
- **If a preference exists in the schema, it needs a test that reads
  it.** `timeout_ms` was declared for weeks before anyone noticed
  nothing consumed it. A one-line assertion "preferences.timeout_ms
  influences runPlan deadline" would have caught this immediately.
- **Merge caller signals + internal deadlines into one
  AbortController.** Two parallel "who fires first" paths create
  corner cases (cleanup order, double-abort). One controller with a
  `reason` field keeps the error shape disambiguated without
  branching at every await.
