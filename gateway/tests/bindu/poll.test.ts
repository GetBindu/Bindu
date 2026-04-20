import { describe, it, expect, vi } from "vitest"
import { sendAndPoll } from "../../src/bindu/client/poll"
import { ErrorCode, BinduError } from "../../src/bindu/protocol/jsonrpc"
import type { Message } from "../../src/bindu/protocol/types"

function jsonResp(body: unknown, init: { status?: number } = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  })
}

const baseMessage: Message = {
  messageId: "m1",
  contextId: "c1",
  taskId: "t1",
  kind: "message",
  role: "user",
  parts: [{ kind: "text", text: "hi" }],
}

describe("sendAndPoll — polling client", () => {
  it("submitted → working → completed, reports one poll", async () => {
    const seq: unknown[] = [
      { jsonrpc: "2.0", id: "1", result: { id: "tsk", contextId: "c1", kind: "task", status: { state: "submitted", timestamp: "t" } } },
      { jsonrpc: "2.0", id: "2", result: { id: "tsk", context_id: "c1", kind: "task", status: { state: "working", timestamp: "t" } } },
      { jsonrpc: "2.0", id: "3", result: { id: "tsk", context_id: "c1", kind: "task", status: { state: "completed", timestamp: "t" }, artifacts: [] } },
    ]
    const fetchMock = vi.fn(async () => jsonResp(seq.shift()))

    const outcome = await sendAndPoll({
      peerUrl: "http://fake",
      message: baseMessage,
      fetch: fetchMock as unknown as typeof fetch,
      backoffMs: [0, 0, 0, 0],
      maxPolls: 5,
    })
    expect(outcome.terminal).toBe(true)
    expect(outcome.task.status.state).toBe("completed")
    // 1 message/send + 2 tasks/get = 3 fetches
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(outcome.polls).toBe(2)
  })

  it("flips taskId casing on -32700 schema mismatch", async () => {
    const seq: unknown[] = [
      // message/send: submitted
      { jsonrpc: "2.0", id: "1", result: { id: "tsk", contextId: "c1", kind: "task", status: { state: "submitted", timestamp: "t" } } },
      // first poll: -32700 (camelCase taskId wasn't accepted)
      { jsonrpc: "2.0", id: "2", error: { code: -32700, message: "schema mismatch" } },
      // retry with snake_case task_id → completed
      { jsonrpc: "2.0", id: "3", result: { id: "tsk", context_id: "c1", kind: "task", status: { state: "completed", timestamp: "t" } } },
    ]
    const seen: any[] = []
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const body = JSON.parse(init.body as string)
      seen.push(body)
      return jsonResp(seq.shift())
    })

    const outcome = await sendAndPoll({
      peerUrl: "http://fake",
      message: baseMessage,
      fetch: fetchMock as unknown as typeof fetch,
      backoffMs: [0, 0, 0, 0],
      maxPolls: 5,
    })
    expect(outcome.task.status.state).toBe("completed")
    // First poll used camelCase, second used snake_case
    expect(seen[1].params).toHaveProperty("taskId")
    expect(seen[2].params).toHaveProperty("task_id")
  })

  it("returns needsAction for input-required without exhausting polls", async () => {
    const seq: unknown[] = [
      { jsonrpc: "2.0", id: "1", result: { id: "tsk", contextId: "c1", kind: "task", status: { state: "submitted", timestamp: "t" } } },
      { jsonrpc: "2.0", id: "2", result: { id: "tsk", context_id: "c1", kind: "task", status: { state: "input-required", timestamp: "t" } } },
    ]
    const fetchMock = vi.fn(async () => jsonResp(seq.shift()))
    const outcome = await sendAndPoll({
      peerUrl: "http://fake",
      message: baseMessage,
      fetch: fetchMock as unknown as typeof fetch,
      backoffMs: [0, 0],
      maxPolls: 5,
    })
    expect(outcome.terminal).toBe(false)
    expect(outcome.needsAction).toBe(true)
    expect(outcome.task.status.state).toBe("input-required")
  })

  it("-32013 InsufficientPermissions surfaces as BinduError", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResp({ jsonrpc: "2.0", id: "1", error: { code: -32013, message: "denied" } }, { status: 403 }),
    )
    await expect(
      sendAndPoll({
        peerUrl: "http://fake",
        message: baseMessage,
        fetch: fetchMock as unknown as typeof fetch,
      }),
    ).rejects.toSatisfy(
      (e: unknown) => e instanceof BinduError && (e as BinduError).code === ErrorCode.InsufficientPermissions,
    )
  })
})
