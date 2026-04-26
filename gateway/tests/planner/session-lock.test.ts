import { describe, it, expect } from "vitest"
import { Effect } from "effect"
import { withSessionLock } from "../../src/planner"
import type { SessionID } from "../../src/session/schema"

/**
 * Regression test for `no-session-concurrency-guard`.
 *
 * Before the fix:
 *   - Two /plan requests on the same session_id ran their planner
 *     loops in parallel.
 *   - Both appended to gateway_messages without coordination, so the
 *     second LLM call could observe the first's half-written tool_use
 *     before its paired tool_result — corrupting the on-disk history
 *     and tripping Anthropic / OpenAI's tool-pairing 400.
 *
 * The fix (src/planner/index.ts):
 *   - Per-session promise chain in `sessionLocks: Map<SessionID, Promise>`.
 *   - Each runPlan installs a fresh tail and awaits the prior tail
 *     before its body runs.
 *   - `Effect.ensuring` releases the lock on success, failure, OR
 *     interruption — so a hung or aborted plan can't deadlock the next.
 *
 * The lock helper is exported so this test can drive it against a
 * controllable inner Effect (mirrors the compaction-dedupe test
 * pattern: pin the invariants in the test, not the production
 * implementation's private state).
 */

const sid = (s: string) => s as unknown as SessionID

describe("withSessionLock", () => {
  it("serializes two concurrent calls on the SAME session", async () => {
    const locks = new Map<SessionID, Promise<unknown>>()
    const events: string[] = []

    let releaseFirst!: () => void
    const firstGate = new Promise<void>((r) => {
      releaseFirst = r
    })

    const inner = (label: string, gate?: Promise<void>) =>
      Effect.gen(function* () {
        events.push(`${label}:start`)
        if (gate) yield* Effect.promise(() => gate)
        events.push(`${label}:end`)
        return label
      })

    // First call holds the lock until we release the gate.
    const p1 = Effect.runPromise(
      withSessionLock(locks, sid("S"), inner("A", firstGate)),
    )
    // Second call queues. Without the lock its `start` would interleave.
    const p2 = Effect.runPromise(withSessionLock(locks, sid("S"), inner("B")))

    // Yield once so both Effects have a chance to schedule.
    await new Promise((r) => setTimeout(r, 5))
    expect(events).toEqual(["A:start"])

    releaseFirst()
    await Promise.all([p1, p2])

    expect(events).toEqual(["A:start", "A:end", "B:start", "B:end"])
  })

  it("does NOT serialize across DIFFERENT sessions", async () => {
    const locks = new Map<SessionID, Promise<unknown>>()
    const events: string[] = []

    let releaseA!: () => void
    const gateA = new Promise<void>((r) => {
      releaseA = r
    })

    const inner = (label: string, gate?: Promise<void>) =>
      Effect.gen(function* () {
        events.push(`${label}:start`)
        if (gate) yield* Effect.promise(() => gate)
        events.push(`${label}:end`)
      })

    const pA = Effect.runPromise(
      withSessionLock(locks, sid("SA"), inner("A", gateA)),
    )
    const pB = Effect.runPromise(withSessionLock(locks, sid("SB"), inner("B")))

    // Different sessions — B can run to completion while A is still
    // holding its own lock.
    await pB
    expect(events).toEqual(["A:start", "B:start", "B:end"])

    releaseA()
    await pA
    expect(events).toEqual(["A:start", "B:start", "B:end", "A:end"])
  })

  it("releases the lock when the holder fails (next caller proceeds)", async () => {
    const locks = new Map<SessionID, Promise<unknown>>()

    const failing = Effect.fail(new Error("boom"))
    const succeeding = Effect.succeed("ok")

    await expect(
      Effect.runPromise(withSessionLock(locks, sid("S"), failing)),
    ).rejects.toThrow("boom")

    // After the prior holder failed, the next caller must NOT inherit
    // the rejection — the chain swallows prior errors so a single
    // failed plan doesn't poison the session forever.
    await expect(
      Effect.runPromise(withSessionLock(locks, sid("S"), succeeding)),
    ).resolves.toBe("ok")

    // And the map is cleaned up after the last caller settles.
    expect(locks.has(sid("S"))).toBe(false)
  })

  it("clears the map entry only when the current tail finishes", async () => {
    const locks = new Map<SessionID, Promise<unknown>>()

    let release1!: () => void
    const gate1 = new Promise<void>((r) => {
      release1 = r
    })
    let release2!: () => void
    const gate2 = new Promise<void>((r) => {
      release2 = r
    })

    const inner = (gate: Promise<void>) =>
      Effect.gen(function* () {
        yield* Effect.promise(() => gate)
      })

    const p1 = Effect.runPromise(withSessionLock(locks, sid("S"), inner(gate1)))
    const p2 = Effect.runPromise(withSessionLock(locks, sid("S"), inner(gate2)))

    // Tail is currently p2.
    expect(locks.has(sid("S"))).toBe(true)

    // Release first holder. p2 is now the active one. Map entry should
    // remain — it tracks the latest tail, not the current holder.
    release1()
    await p1
    expect(locks.has(sid("S"))).toBe(true)

    // Release second holder. Now nothing is queued, map entry clears.
    release2()
    await p2
    expect(locks.has(sid("S"))).toBe(false)
  })
})
