import { describe, it, expect } from "vitest"

/**
 * Regression test for the "concurrent compaction races" bug.
 *
 * Before the fix:
 *   - Two /plan requests on the same session_id would both call
 *     compactIfNeeded.
 *   - Both would read the same history, both would summarize via the
 *     LLM (double cost), both would UPDATE
 *     gateway_sessions.compaction_summary — last writer wins.
 *   - LLMs are non-deterministic even at temp=0.2, so the two summaries
 *     diverge. The losing summary's facts silently vanish.
 *
 * The fix (src/session/compaction.ts):
 *   - Application-layer dedupe: an in-process
 *     `Map<SessionID, Promise<CompactOutcome>>` keyed by session id.
 *   - First caller kicks off the producer and stores its promise in
 *     the map.
 *   - Concurrent callers for the same session find the existing entry
 *     and AWAIT THE SAME PROMISE — no second producer run.
 *   - The map entry is cleared in a finally block when the producer
 *     resolves or rejects.
 *
 * This test exercises the dedupe wrapper's semantics directly. The
 * implementation in compaction.ts is a closure over `inflight` Map —
 * not exported — so we rebuild the same pattern here as the spec.
 * If someone edits compaction.ts's dedupe(), the two must stay in sync;
 * the assertions below pin the invariants.
 */

// Mirror of the production dedupe so the test is hermetic.
function makeDedupe<K, V>() {
  const inflight = new Map<K, Promise<V>>()
  return function dedupe(key: K, producer: () => Promise<V>): Promise<V> {
    const existing = inflight.get(key)
    if (existing) return existing
    const p = producer().finally(() => {
      if (inflight.get(key) === p) inflight.delete(key)
    })
    inflight.set(key, p)
    return p
  }
}

describe("compaction dedupe wrapper", () => {
  it("second concurrent call reuses the first producer's promise (no duplicate LLM)", async () => {
    const dedupe = makeDedupe<string, string>()

    let producerRuns = 0
    let resolve!: (v: string) => void
    const gate = new Promise<string>((r) => {
      resolve = r
    })

    const producer = () => {
      producerRuns += 1
      return gate
    }

    // First caller kicks off the producer.
    const p1 = dedupe("sess-A", producer)
    // Second concurrent caller MUST see the in-flight entry and NOT
    // run the producer again.
    const p2 = dedupe("sess-A", producer)

    expect(producerRuns).toBe(1)
    // They must resolve to the same value, from the same underlying promise.
    expect(p1).toBe(p2)

    resolve("summary-A")
    await expect(p1).resolves.toBe("summary-A")
    await expect(p2).resolves.toBe("summary-A")
  })

  it("after the producer settles, the next call starts a fresh producer", async () => {
    const dedupe = makeDedupe<string, string>()

    let runs = 0
    const producer = async () => {
      runs += 1
      return `run-${runs}`
    }

    const first = await dedupe("sess-A", producer)
    expect(first).toBe("run-1")

    // Entry cleared on settle → next call starts again.
    const second = await dedupe("sess-A", producer)
    expect(second).toBe("run-2")
    expect(runs).toBe(2)
  })

  it("different session keys do NOT share a producer", async () => {
    const dedupe = makeDedupe<string, string>()

    let runs = 0
    const producer = async () => {
      runs += 1
      // Capture BEFORE awaiting so two concurrent invocations don't both
      // read the final post-increment value.
      const myRun = runs
      await new Promise((r) => setTimeout(r, 5))
      return `n-${myRun}`
    }

    const [a, b] = await Promise.all([
      dedupe("sess-A", producer),
      dedupe("sess-B", producer),
    ])
    expect(runs).toBe(2)
    expect(new Set([a, b]).size).toBe(2)
  })

  it("producer rejection clears the entry so retry is possible", async () => {
    const dedupe = makeDedupe<string, string>()

    let attempts = 0
    const flaky = async () => {
      attempts += 1
      if (attempts === 1) throw new Error("boom")
      return "ok"
    }

    await expect(dedupe("sess-A", flaky)).rejects.toThrow("boom")
    // After the failure the inflight entry must be cleared so the next
    // call gets a fresh chance. If the old entry lingered, it'd re-reject
    // the cached rejection or refuse to run.
    await expect(dedupe("sess-A", flaky)).resolves.toBe("ok")
    expect(attempts).toBe(2)
  })
})
