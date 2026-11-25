# Worker Concurrency and Cancellation

One stalled provider call used to freeze an entire agent: the worker awaited
every task to completion before looking at the next one, so a single hung
LLM request queued every other task — and even the cancel aimed at it —
behind itself. Since #619 the worker dispatches tasks concurrently and
`tasks/cancel` interrupts in-flight work. This page tells you what you get,
what is guaranteed, and where the boundaries are.

## Turning concurrency on

```bash
AGENT__MAX_CONCURRENT_TASKS=3 bindu serve
```

The default is `1`, which keeps strict serial execution — upgrading changes
nothing until you raise the cap. The cap bounds how many runs execute at
once in one agent process; it is the spend bound for provider calls.

## What is guaranteed

- **Same context never overlaps.** Tasks sharing a `context_id` run
  serially in arrival order, whatever the cap. Context-history agents build
  their message list from the pre-turn history; overlapping them would
  corrupt it. This is not configurable.
- **Cancel never queues behind its target.** Control operations bypass the
  concurrency gates, so `tasks/cancel` interrupts a running task even at
  cap 1 with the queue full.
- **One failure stays one failure.** A handler exception marks its own task
  failed; siblings and the dispatch loop keep going.
- **Terminal states stick.** Worker writes are guarded compare-and-swap
  updates: a run that finishes after its task was canceled gets its late
  result discarded — state, artifacts, and messages atomically — instead of
  overwriting `canceled` with `completed`.
- **Paid tasks stay reconcilable.** Under x402 settle-first, the settlement
  receipt is persisted to the task before the handler runs. If the run is
  then canceled, the receipt is re-tagged `payment-orphaned` so you can find
  canceled-but-paid tasks and refund them manually. Both writes are bounded
  and best-effort, so do not sweep for the orphan tag alone: a canceled
  task whose metadata carries a settlement receipt needs reconciliation
  even when the `payment-orphaned` tag is missing.
- **Graceful shutdown loses no queued work.** A task interrupted mid-run is
  finalized as `canceled` (re-running half-executed handlers is not safe).
  A task that never started is handed back to the scheduler and stays
  `submitted` for the next worker — unless the scheduler refuses the send
  or does not accept it within 5 s, in which case the task is finalized as
  `canceled` rather than left stranded with its operation consumed.

## What to know before relying on it

- **Ordering across contexts is not global FIFO.** A task waiting for its
  context lock yields its slot to other contexts: submit A1, A2 (same
  context), B1, and at cap 1 you can observe A1, B1, A2. Per-context order
  is always preserved; cross-context order favors not blocking strangers
  behind a busy context.
- **Synchronous handlers do not overlap.** A plain `def` handler executes
  on the event loop, so it blocks everything — including cancel delivery —
  until it returns, whatever the cap. Write `async def` handlers (awaiting
  your model SDK) to benefit from concurrency and interruption.
- **One process, one worker.** The cap, the context locks, and the cancel
  interrupts all live inside a single agent process. Running two workers
  against one Redis queue is unsupported today: each operation is delivered
  to exactly one consumer, so a cancel can land on the worker that is not
  running the task, and two replicas can overlap a shared context. Scale a
  single agent up (raise the cap), not out, until replica-aware routing and
  distributed context locks exist.
- **A crash can drop consumed operations.** The dispatcher drains the
  scheduler eagerly (that is what keeps cancels from queueing), so with the
  Redis scheduler a hard kill loses operations that were popped but not yet
  finished. A task that never started stays `submitted`; one that was
  mid-run stays `working` — sweep for both states after a hard kill, or
  you will miss interrupted runs. Graceful shutdown requeues the former —
  falling back to `canceled` when the scheduler refuses the send or times
  out (5 s) — and finalizes the latter as `canceled` (see above). The
  planned fix is a separate control channel plus bounded prefetch with
  acknowledged delivery.

## Verifying it on your agent

Send three `message/send` requests with distinct `contextId`s and watch the
working windows overlap (three 5 s calls finish in ~5 s wall, not ~15 s).
Send two with the same `contextId` and they run back to back in order. Then
`tasks/cancel` a long run mid-flight: the state flips to `canceled`
immediately and the provider-side connection is torn down.
