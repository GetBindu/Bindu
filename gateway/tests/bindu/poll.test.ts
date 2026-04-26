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

  it("signal abort mid-backoff wakes the loop and issues cancel", async () => {
    // Peer keeps returning "working" forever. We'd wait 10s between polls
    // under default backoff — the test would hang if abort didn't cut it.
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const body = JSON.parse(init.body as string)
      if (body.method === "message/send") {
        return jsonResp({
          jsonrpc: "2.0",
          id: body.id,
          result: {
            id: "tsk",
            contextId: "c1",
            kind: "task",
            status: { state: "submitted", timestamp: "t" },
          },
        })
      }
      if (body.method === "tasks/get") {
        return jsonResp({
          jsonrpc: "2.0",
          id: body.id,
          result: {
            id: "tsk",
            context_id: "c1",
            kind: "task",
            status: { state: "working", timestamp: "t" },
          },
        })
      }
      // tasks/cancel — ack
      return jsonResp({ jsonrpc: "2.0", id: body.id, result: {} })
    })

    const ac = new AbortController()
    // Fire abort after 30ms — well inside the first backoff boundary.
    setTimeout(() => ac.abort(), 30)
    const start = Date.now()
    const p = sendAndPoll({
      peerUrl: "http://fake",
      message: baseMessage,
      fetch: fetchMock as unknown as typeof fetch,
      backoffMs: [10_000], // would block for 10s if abort didn't wake it
      maxPolls: 60,
      signal: ac.signal,
    })
    await expect(p).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof BinduError &&
        (e as BinduError).code === ErrorCode.AbortedByCaller &&
        ((e as BinduError).data as any)?.reason === "signal",
    )
    expect(Date.now() - start).toBeLessThan(500)
    // Verify a tasks/cancel was dispatched to the peer.
    const calls = fetchMock.mock.calls
    const sawCancel = calls.some((c: unknown[]) => {
      const init = c[1] as RequestInit
      const body = JSON.parse(init.body as string)
      return body.method === "tasks/cancel"
    })
    expect(sawCancel).toBe(true)
  })

  it("deadlineMs expiry aborts with reason=deadline", async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const body = JSON.parse(init.body as string)
      if (body.method === "message/send") {
        return jsonResp({
          jsonrpc: "2.0",
          id: body.id,
          result: {
            id: "tsk",
            contextId: "c1",
            kind: "task",
            status: { state: "submitted", timestamp: "t" },
          },
        })
      }
      if (body.method === "tasks/get") {
        return jsonResp({
          jsonrpc: "2.0",
          id: body.id,
          result: {
            id: "tsk",
            context_id: "c1",
            kind: "task",
            status: { state: "working", timestamp: "t" },
          },
        })
      }
      return jsonResp({ jsonrpc: "2.0", id: body.id, result: {} })
    })

    const start = Date.now()
    await expect(
      sendAndPoll({
        peerUrl: "http://fake",
        message: baseMessage,
        fetch: fetchMock as unknown as typeof fetch,
        backoffMs: [10_000],
        maxPolls: 60,
        deadlineMs: 50,
      }),
    ).rejects.toSatisfy(
      (e: unknown) =>
        e instanceof BinduError &&
        (e as BinduError).code === ErrorCode.AbortedByCaller &&
        ((e as BinduError).data as any)?.reason === "deadline",
    )
    expect(Date.now() - start).toBeLessThan(500)
  })

  it("deadlineMs that never trips still lets normal runs complete", async () => {
    const seq: unknown[] = [
      { jsonrpc: "2.0", id: "1", result: { id: "tsk", contextId: "c1", kind: "task", status: { state: "submitted", timestamp: "t" } } },
      { jsonrpc: "2.0", id: "2", result: { id: "tsk", context_id: "c1", kind: "task", status: { state: "completed", timestamp: "t" } } },
    ]
    const fetchMock = vi.fn(async () => jsonResp(seq.shift()))
    const outcome = await sendAndPoll({
      peerUrl: "http://fake",
      message: baseMessage,
      fetch: fetchMock as unknown as typeof fetch,
      backoffMs: [0],
      maxPolls: 5,
      deadlineMs: 60_000,
    })
    expect(outcome.terminal).toBe(true)
  })
})
