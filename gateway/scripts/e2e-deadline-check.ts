/**
 * End-to-end check: live stuck peer + deadlineMs → ground-truth behavior.
 *
 * Run: npx tsx scripts/e2e-deadline-check.ts
 *
 * This is a human-runnable smoke test, not part of the CI suite. It
 * exists to prove the fix against a real HTTP server (no mocked fetch)
 * and to print the timings so we can see with our own eyes that a
 * stuck peer does NOT cause the gateway to wait through the full
 * backoff ladder.
 */

import { startMockBinduAgent } from "../tests/helpers/mock-bindu-agent"
import { sendAndPoll } from "../src/bindu/client/poll"

async function main() {
  const handle = await startMockBinduAgent({
    name: "stuck-research",
    respond: (s) => s,
    stuck: true,
  })
  console.log(`[e2e] stuck mock peer listening at ${handle.url}`)

  try {
    // Case 1: external AbortSignal fires — simulates client-disconnect.
    console.log("\n[e2e] case 1: client-disconnect after 75ms, default 60 polls × up to 10s backoff")
    const ac = new AbortController()
    setTimeout(() => ac.abort(), 75)
    const start1 = Date.now()
    try {
      await sendAndPoll({
        peerUrl: handle.url,
        message: {
          messageId: "m1",
          contextId: "c1",
          taskId: "t1",
          kind: "message",
          role: "user",
          parts: [{ kind: "text", text: "analyze the quarterly filings" }],
        },
        // use DEFAULT backoff + maxPolls (worst case 5 min) on purpose.
        signal: ac.signal,
      })
      console.log("[e2e] FAIL: sendAndPoll should have thrown")
      process.exit(1)
    } catch (e: any) {
      const elapsed = Date.now() - start1
      console.log(
        `[e2e]   → threw after ${elapsed}ms  code=${e.code}  reason=${e.data?.reason}  msg="${e.message}"`,
      )
      if (elapsed > 2000) {
        console.log("[e2e] FAIL: abort took too long to wake the loop")
        process.exit(1)
      }
      if (e.code !== -32040 || e.data?.reason !== "signal") {
        console.log("[e2e] FAIL: wrong error shape")
        process.exit(1)
      }
    }

    // Case 2: deadlineMs fires — simulates plan-level budget expiry.
    console.log("\n[e2e] case 2: deadlineMs=200, default 60 polls × up to 10s backoff")
    const start2 = Date.now()
    try {
      await sendAndPoll({
        peerUrl: handle.url,
        message: {
          messageId: "m2",
          contextId: "c2",
          taskId: "t2",
          kind: "message",
          role: "user",
          parts: [{ kind: "text", text: "this is a multi-hour research plan" }],
        },
        deadlineMs: 200,
      })
      console.log("[e2e] FAIL: sendAndPoll should have thrown")
      process.exit(1)
    } catch (e: any) {
      const elapsed = Date.now() - start2
      console.log(
        `[e2e]   → threw after ${elapsed}ms  code=${e.code}  reason=${e.data?.reason}  msg="${e.message}"`,
      )
      if (elapsed > 2000) {
        console.log("[e2e] FAIL: deadline took too long")
        process.exit(1)
      }
      if (e.code !== -32040 || e.data?.reason !== "deadline") {
        console.log("[e2e] FAIL: wrong error shape")
        process.exit(1)
      }
    }

    // Case 3: long deadline, peer actually responds → normal success path.
    console.log("\n[e2e] case 3: non-stuck peer + deadline that never fires → success")
    const fastHandle = await startMockBinduAgent({
      name: "fast",
      respond: (s) => `echo: ${s}`,
    })
    try {
      const start3 = Date.now()
      const outcome = await sendAndPoll({
        peerUrl: fastHandle.url,
        message: {
          messageId: "m3",
          contextId: "c3",
          taskId: "t3",
          kind: "message",
          role: "user",
          parts: [{ kind: "text", text: "hello" }],
        },
        deadlineMs: 60_000,
        backoffMs: [10],
      })
      const elapsed = Date.now() - start3
      const artText = (outcome.task.artifacts?.[0]?.parts?.[0] as any)?.text ?? "<none>"
      console.log(
        `[e2e]   → completed in ${elapsed}ms  state=${outcome.task.status.state}  artifact="${artText}"`,
      )
      if (outcome.task.status.state !== "completed" || artText !== "echo: hello") {
        console.log("[e2e] FAIL: unexpected outcome")
        process.exit(1)
      }
    } finally {
      await fastHandle.close()
    }

    console.log("\n[e2e] ALL CASES PASSED")
  } finally {
    await handle.close()
  }
}

main().catch((e) => {
  console.error("[e2e] crashed:", e)
  process.exit(1)
})
