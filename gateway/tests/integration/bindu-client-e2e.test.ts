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
})
