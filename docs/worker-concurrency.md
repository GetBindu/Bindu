# Worker Concurrency and Cancellation

One stalled provider call used to freeze an entire agent: the worker awaited
every task to completion before looking at the next one, so a single hung
LLM request queued every other task — and even the cancel aimed at it —
behind itself. Since #619 the worker dispatches tasks concurrently and
`tasks/cancel` interrupts in-flight work. This page tells you what you get,
what is guaranteed, and where the boundaries are.

## Turning concurrency on

```bash
AGENT__MAX_CONCURRENT_TASKS=3 uv run python my_agent.py
```

For a TypeScript (or other gRPC SDK) agent, set it in the environment you
launch the agent from — the SDK passes it through to the core it spawns.

The default is `1`, which keeps strict serial execution — upgrading changes
nothing until you raise the cap. The cap bounds how many runs execute at
once in one agent process. It limits tasks, not model calls: one task
whose handler makes several calls at once still makes all of them.

## Your handler has to be async

Raising the cap does nothing for a plain `def` handler. A sync handler runs
on the event loop, so while it waits on the model, nothing else in the
process moves — not the next task, not the cancel aimed at it. Most
examples in `examples/` use a sync handler because it is the shortest thing
that works; they run correctly, just one task at a time.

The fix is usually one line. With agno:

```python
# Serial: blocks the event loop for the whole model call.
def handler(messages):
    return agent.run(input=messages)

# Concurrent and cancellable: the model call is an await point.
async def handler(messages):
    return await agent.arun(input=messages)
```

Any async client works the same way (`AsyncOpenAI`, LangChain's `ainvoke`,
`httpx.AsyncClient`): what matters is that the slow part is awaited.
TypeScript SDK handlers are already async, so they get concurrency and
cancellation as soon as the cap is raised.

How far a cancel reaches depends on that call chain. When your handler
awaits the model call directly (agno `arun`, `AsyncOpenAI`), cancel aborts
the in-flight request. Frameworks that run steps in their own tasks may
let the step already running finish first — with LangGraph we observed
the current node's model call complete about 13 s after the cancel, then
the graph stopped before its next call. Either way the task stays
`canceled` and the late result is discarded; you still pay for whatever
calls were already in flight and didn't stop.

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
  even when the `payment-orphaned` tag is missing. If storage was
  unreachable for both writes, the worker's error log carries the full
  settlement metadata as the record of last resort.
- **Graceful shutdown loses no queued work.** A task interrupted mid-run is
  finalized as `canceled` (re-running half-executed handlers is not safe).
  With the Redis scheduler, a task that never started is handed back to
  the queue and stays `submitted` for the next worker; if that send fails
  or times out (5 s), the task stays `submitted` with an error logged —
  re-enqueue or resubmit it. With the in-memory scheduler (whose buffer
  dies with the process) never-started tasks are finalized as `canceled`.

## What to know before relying on it

- **Ordering across contexts is not global FIFO.** A task waiting for its
  context lock yields its slot to other contexts: submit A1, A2 (same
  context), B1, and at cap 1 you can observe A1, B1, A2. Per-context order
  is always preserved; cross-context order favors not blocking strangers
  behind a busy context.
- **Synchronous handlers do not overlap.** A plain `def` handler executes
  on the event loop, so it blocks everything — including cancel delivery —
  until it returns, whatever the cap (see "Your handler has to be async").
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
  you will miss interrupted runs. Graceful shutdown requeues the former
  on Redis (leaving them `submitted` with an error log if the send fails)
  and finalizes the latter as `canceled` (see above). The planned fix is a
  separate control channel plus bounded prefetch with acknowledged
  delivery.

## Verifying it on your agent

Send three `message/send` requests with distinct `contextId`s and watch the
working windows overlap (three 5 s calls finish in ~5 s wall, not ~15 s).
Send two with the same `contextId` and they run back to back in order. Then
`tasks/cancel` a long run mid-flight: the state flips to `canceled`
immediately and stays there; with a directly awaited model call, the
provider-side connection is torn down too.

If your test prompts are short or vague, the model may answer with a
clarifying question and the task stops in `input-required` instead of
`completed` (Bindu's default structured-response prompt invites this).
Wait for that state too, or make the prompt specific ("pick sensible
defaults, don't ask questions").
