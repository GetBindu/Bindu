---
id: 2026-04-18-spawnreader-fiber-leak
title: SSE reader fibers never terminated, leaking PubSub subscribers per request
severity: critical
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: gateway/api
commit: 9e49d97
---

## Symptom

Each `POST /plan` request leaked five Effect fibers and five PubSub
subscriptions. Symptoms accumulate over days or weeks of uptime:

- Monotonically growing heap (`FiberImpl`, `Subscription`,
  closure-captured `AbortController` and `ReadableStreamController`).
- Event publishes get slower linearly with total requests-ever, because
  every publish fans out to every accumulated zombie subscriber.
- After several thousand requests: observable event-loop lag, then
  eventual OOM on long-running gateway processes.

Not a crash. A slow leak that passes the test suite and starts to bite
in production after hours or days of traffic.

## Root cause

`spawnReader` in `gateway/src/api/plan-route.ts:155-174` (pre-fix):

```ts
function spawnReader<T>(signal, source, cb) {
  void Effect.runPromise(
    Stream.runForEach(source, (evt) =>
      Effect.promise(async () => {
        if (signal.aborted) return          // only skips WRITES
        try { await cb(evt) } catch { /* swallow */ }
      }),
    ),
  ).catch(() => { /* stream shut down */ })
}
```

`Stream.fromPubSub(ps)` is an infinite stream — it keeps yielding as
long as the PubSub is alive. `Stream.runForEach` loops forever. The
`signal.aborted` check inside the callback suppressed the `writeSSE`
call but did nothing to stop the upstream iterator from pulling the next
event.

The handler's `finally { ac.abort() }` did nothing to this fiber.
`AbortController` is a DOM / fetch primitive; Effect's streams don't
listen to it unless explicitly wired in.

Mental model that led to the bug: "when the request ends, the abort
signal fires, and my callback sees `signal.aborted === true` so it
returns early." The callback DID return early — but the fiber kept
pulling the next event, and the next, and the next. The early return
was a write guard, not a lifecycle hook.

## Fix

- `abortEffect(signal)` helper: converts an `AbortSignal` into an
  `Effect` that resolves when the signal fires, using `Effect.callback`
  (the Effect 4.0 replacement for `Effect.async`).
- Pipe the reader's source stream through
  `Stream.interruptWhen(abortEffect(signal))` so the fiber terminates
  cleanly when the handler's `finally { ac.abort() }` runs.
- Drop the prior `await new Promise(r => setTimeout(r, 100))` flush
  hack from the success path — the interrupt gates the lifecycle
  deterministically.

Regression test at `gateway/tests/api/plan-route-filter.test.ts`: forks
a reader fiber, publishes an event, aborts the signal, then awaits the
fiber. If `interruptWhen` is broken, the await hangs and Vitest fails
on timeout.

## Why the tests didn't catch it

Three compounding reasons:

1. **No resource-leak test** existed. Tests ran single short scenarios
   and asserted correctness of outputs — never that resources were
   released.
2. **Test duration was too short** to observe leak accumulation. A
   unit test that makes one request and exits can't see a fiber that
   "never terminates" — the process exits and takes the fiber with it.
3. **The fiber's cost per iteration is tiny.** You'd need thousands of
   requests plus heap snapshots to see the leak in a test environment;
   the framework-level cost isn't observable in ms-scale test timings.

The failure mode is inherently a production-shape problem: long-running
process + sustained request volume + heap growth over time. Unit tests
are the wrong tool; a load-test harness would be the right one.

## Class of bug — where else to watch

**"Infinite streams tied to request lifecycle"** — any time code does
`Stream.runForEach` on a stream that doesn't naturally terminate, the
stream needs an explicit interrupt trigger. The `signal.aborted` guard
pattern is a footgun: it *looks* like it handles cancellation but
only handles partial cancellation (write suppression), not lifecycle
tear-down.

Other places this shape can exist in this codebase:

- Any future streaming API (inbound Bindu server, `/message/stream`,
  admin dashboards) that subscribes to a PubSub per request.
- The `session.history()` path does NOT use infinite streams today, but
  any lazy-loading variant added later could have the same shape.
- Background workers reading from a queue (`gateway/src/bus/` has
  `subscribeAll` exposed but unused today — any consumer that appears
  needs interrupt wiring).

Rule of thumb: **if a stream doesn't terminate on its own, every
`runForEach` on it must be paired with a `Stream.interruptWhen` tied
to the caller's scope.** `AbortSignal` alone is not a lifecycle hook
for Effect streams — bridge it through `Effect.callback` first.
