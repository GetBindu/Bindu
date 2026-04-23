import { describe, it, expect, afterEach } from "vitest"
import { startMockBinduAgent, type MockAgentHandle } from "../helpers/mock-bindu-agent"
import { sendAndPoll } from "../../src/bindu/client/poll"

/**
 * End-to-end test for the Bindu polling client against an in-process mock
 * Bindu agent. Exercises: message/send → tasks/get → artifact extraction,
 * without Supabase or the AI SDK or a real LLM.
 *
 * This is the closest we get to the Phase 0 dry-run for CI — same wire
 * shape, deterministic behavior, runs in ~100ms.
 */

describe("Bindu client E2E — against in-process mock agent", () => {
  let handle: MockAgentHandle | null = null

  afterEach(async () => {
    if (handle) {
      await handle.close()
      handle = null
    }
  })

  it("echoes user text via message/send + tasks/get round-trip", async () => {
    handle = await startMockBinduAgent({
      name: "echo",
      respond: (input) => input,
    })

    const outcome = await sendAndPoll({
      peerUrl: handle.url,
      message: {
        messageId: "m1",
        contextId: "c1",
        taskId: "t1",
        kind: "message",
        role: "user",
        parts: [{ kind: "text", text: "hello gateway" }],
      },
      backoffMs: [10],
      maxPolls: 5,
    })

    expect(outcome.terminal).toBe(true)
    expect(outcome.task.status.state).toBe("completed")
    expect(outcome.task.artifacts?.length).toBe(1)

    const art = outcome.task.artifacts![0]
    expect((art as any).artifactId ?? (art as any).artifact_id).toBeTruthy()
    const textPart = art.parts?.[0]
    expect(textPart?.kind).toBe("text")
    if (textPart?.kind === "text") {
      expect(textPart.text).toBe("hello gateway")
    }
  })

  it("uppercase transform proves the agent's respond fn runs", async () => {
    handle = await startMockBinduAgent({
      name: "upper",
      respond: (input) => input.toUpperCase(),
    })

    const outcome = await sendAndPoll({
      peerUrl: handle.url,
      message: {
        messageId: "m1",
        contextId: "c1",
        taskId: "t1",
        kind: "message",
        role: "user",
        parts: [{ kind: "text", text: "mixed Case" }],
      },
      backoffMs: [10],
      maxPolls: 5,
    })

    expect(outcome.task.status.state).toBe("completed")
    const textPart = outcome.task.artifacts![0].parts![0]
    if (textPart.kind === "text") {
      expect(textPart.text).toBe("MIXED CASE")
    }
  })

  it("handles normalize correctly — snake_case task body parses", async () => {
    handle = await startMockBinduAgent({
      name: "e",
      respond: (s) => s,
    })

    const outcome = await sendAndPoll({
      peerUrl: handle.url,
      message: {
        messageId: "m1",
        contextId: "ctx-abc",
        taskId: "t1",
        kind: "message",
        role: "user",
        parts: [{ kind: "text", text: "x" }],
      },
      backoffMs: [10],
      maxPolls: 5,
    })

    // Mock emits `context_id` (snake); our Normalize.fromWire("task", ...)
    // turns it into `contextId` on the parsed Task object.
    expect(outcome.task.contextId).toBeTruthy()
  })

  it("deadline fires against a stuck real peer and issues cancel", async () => {
    // Direct end-to-end proof: spin up a real HTTP mock that never
    // advances past "working", call it with a short deadline, and
    // verify the client (1) wakes from backoff promptly, (2) throws
    // AbortedByCaller with reason=deadline, and (3) sends tasks/cancel
    // to the peer. This is the ground-truth behavior guarded by the
    // poll-budget-unbounded-wall-clock fix.
    handle = await startMockBinduAgent({
      name: "stuck",
      respond: (s) => s,
      stuck: true,
    })

    // Observe cancel by attaching a request interceptor via an
    // additional fetch that records methods. Simplest approach: just
    // check that after the deadline throws, the peer received a
    // tasks/cancel — we verify by polling tasks/get for the
    // canceled state, but the mock's state machine doesn't track cancel
    // outcome after stuck=true (it just returns working). Instead, we
    // assert timing + error shape, which is what we care about for the
    // fix. The cancel dispatch itself is covered by the unit test.
    const start = Date.now()
    await expect(
      sendAndPoll({
        peerUrl: handle.url,
        message: {
          messageId: "m1",
          contextId: "c1",
          taskId: "t1",
          kind: "message",
          role: "user",
          parts: [{ kind: "text", text: "this will never finish" }],
        },
        backoffMs: [10_000], // would block 10s per poll if deadline didn't wake it
        maxPolls: 60,
        deadlineMs: 150,
      }),
    ).rejects.toSatisfy((e: unknown) => {
      const be = e as { code?: number; data?: { reason?: string } }
      return be?.code === -32040 && be?.data?.reason === "deadline"
    })
    const elapsed = Date.now() - start
    expect(elapsed).toBeLessThan(2000) // well under the 10s backoff
    expect(elapsed).toBeGreaterThanOrEqual(100) // at least the deadline
  })
})
