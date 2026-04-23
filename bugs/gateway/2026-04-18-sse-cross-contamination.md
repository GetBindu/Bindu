---
id: 2026-04-18-sse-cross-contamination
title: SSE events leaked across concurrent /plan requests
severity: critical
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: gateway/api
commit: 484b6b8
---

## Symptom

Two clients making concurrent `POST /plan` requests received each other's
Server-Sent Event frames. Client A's terminal saw Client B's
`text.delta`, `task.started`, `task.artifact`, and `final` events mixed
into its own stream — including the agent name, skill id, and tool output
content from B's plan.

In multi-tenant deployments this is a **cross-tenant information
disclosure**: tenant A could observe tenant B's agent interactions, tool
inputs, and outputs in real time.

## Root cause

The handler in `gateway/src/api/plan-route.ts:62-123` (pre-fix) subscribed
to the global event bus with no filter:

```ts
spawnReader(ac.signal, bus.subscribe(PromptEvent.TextDelta), async (evt) => {
  await stream.writeSSE({ ... })
})
```

`bus.subscribe(PromptEvent.TextDelta)` returns a stream of **every**
`session.prompt.text` event published anywhere in the process — the bus
has no built-in per-session partitioning, and the subscriber never
filtered on `evt.properties.sessionID`. The subscription was also set up
BEFORE the session was resolved, so at the point of subscription the
handler had no sessionID to filter on.

Mental model that led to the bug: "the bus delivers events to whoever
listens, and my handler only listens during my request." True, but every
concurrent request also listens at the same time, and events aren't
tenancy-aware.

## Fix

- Split `planner.startPlan` into `prepareSession` + `runPlan` so the SSE
  handler learns `sessionID` before opening the stream.
- Pipe every `bus.subscribe()` through
  `Stream.filter((e) => e.properties.sessionID === sessionCtx.sessionID)`.
- Emit the `session` frame first (previously last) so clients correlate
  subsequent frames from the start.

See commit [484b6b8](../../commit/484b6b8) and the regression test at
`gateway/tests/api/plan-route-filter.test.ts` — two concurrent subscribers
with different session IDs; each must see only its own deltas.

## Why the tests didn't catch it

No test exercised two concurrent `/plan` requests. The existing 23 tests
were all single-session: protocol parsing, signature verification, polling
semantics, and an E2E against a mock Bindu agent. Concurrency as a class
of test was simply absent from the suite.

A secondary reason: the tests that did run the handler path (none, in
practice — the handler was only exercised by hand via `curl`) would not
have tripped the bug with a single request, because a single subscriber
receiving "every" event is indistinguishable from "only my events" when
only one session is in flight.

## Class of bug — where else to watch

**"Global pub-sub without a tenancy filter"** is the pattern. Anywhere
we call `bus.subscribe(...)` or subscribe to any singleton PubSub, the
subscriber must filter on whatever tenancy key the code path is operating
on. Specific other places this could hide:

- A future `/message/stream` SSE endpoint if it follows the same handler
  shape without copying the filter pattern.
- Any admin or observability dashboard that taps `bus.subscribeAll()`
  and surfaces events to an operator — must scope by tenant before
  rendering.
- The inbound Bindu server (Phase 3) will receive events from remote
  peers. If those get published onto the same bus without peer-id
  tagging, cross-peer leakage becomes possible.
- Any websocket or long-poll endpoint added later. The bus pattern will
  look tempting; the filter must be non-optional.

Rule of thumb: **every `bus.subscribe` call should be paired with a
`Stream.filter` tied to the request's tenancy key, at the call site.**
If the filter lives anywhere else (middleware, wrapper), it's easy to
forget for new subscribers.
