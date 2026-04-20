import { createServer, type Server } from "http"
import type { AddressInfo } from "net"

/**
 * In-process mock Bindu agent for integration tests.
 *
 * Implements the minimum wire surface our client exercises:
 *   GET  /.well-known/agent.json      — AgentCard
 *   POST /                            — JSON-RPC 2.0:
 *                                          message/send  → Task (submitted)
 *                                          tasks/get     → Task (completed, with artifact)
 *                                          tasks/cancel  → Task (canceled)
 *
 * Behavior is deterministic — you hand the mock a `respond` function that
 * transforms the incoming user text into the output artifact text. Any
 * other wire details (casing, state transitions) are fixed.
 */

export interface MockAgentConfig {
  /** Name surfaced in AgentCard.name. */
  name: string
  /** Given the incoming user text, returns the artifact text to echo back. */
  respond: (userText: string) => string
  /** Skills to expose in the AgentCard. Defaults to one passthrough skill. */
  skills?: Array<{ id: string; description: string }>
  /** DID to expose in capabilities.extensions (optional). */
  did?: string
}

export interface MockAgentHandle {
  url: string
  port: number
  close: () => Promise<void>
}

export async function startMockBinduAgent(cfg: MockAgentConfig): Promise<MockAgentHandle> {
  const skills = cfg.skills ?? [{ id: "echo", description: "Echo back the user's text" }]
  const tasks = new Map<string, { contextId: string; input: string; state: string }>()

  const server: Server = createServer(async (req, res) => {
    const url = req.url ?? "/"
    const setJson = () => res.setHeader("Content-Type", "application/json")

    if (req.method === "GET" && url === "/.well-known/agent.json") {
      setJson()
      res.end(
        JSON.stringify({
          id: cfg.did ?? "mock-agent-" + cfg.name,
          name: cfg.name,
          description: `Mock ${cfg.name} agent for testing`,
          url: `http://localhost:${(server.address() as AddressInfo).port}`,
          version: "test",
          protocolVersion: "1.0.0",
          kind: "agent",
          capabilities: cfg.did
            ? {
                streaming: false,
                pushNotifications: false,
                extensions: [{ uri: cfg.did, description: "DID for test", required: false }],
              }
            : { streaming: false, pushNotifications: false },
          skills: skills.map((s) => ({ id: s.id, name: s.id, description: s.description })),
          defaultInputModes: ["text/plain", "application/json"],
          defaultOutputModes: ["text/plain", "application/json"],
        }),
      )
      return
    }

    if (req.method !== "POST" || url !== "/") {
      res.statusCode = 404
      res.end()
      return
    }

    const body = await readBody(req)
    const rpc = JSON.parse(body)

    if (rpc.method === "message/send") {
      const message = rpc.params?.message
      const taskId = message?.taskId ?? crypto.randomUUID()
      const contextId = message?.contextId ?? crypto.randomUUID()
      const userText =
        (message?.parts as Array<{ kind?: string; text?: string }>)?.find(
          (p) => p.kind === "text",
        )?.text ?? ""
      tasks.set(taskId, { contextId, input: userText, state: "submitted" })

      setJson()
      res.end(
        JSON.stringify({
          jsonrpc: "2.0",
          id: rpc.id,
          result: {
            id: taskId,
            context_id: contextId,
            kind: "task",
            status: { state: "submitted", timestamp: new Date().toISOString() },
          },
        }),
      )
      return
    }

    if (rpc.method === "tasks/get") {
      const taskId: string | undefined = rpc.params?.taskId ?? rpc.params?.task_id
      if (!taskId || !tasks.has(taskId)) {
        setJson()
        res.end(
          JSON.stringify({
            jsonrpc: "2.0",
            id: rpc.id,
            error: { code: -32001, message: "task not found" },
          }),
        )
        return
      }
      const t = tasks.get(taskId)!
      t.state = "completed"

      setJson()
      res.end(
        JSON.stringify({
          jsonrpc: "2.0",
          id: rpc.id,
          result: {
            id: taskId,
            context_id: t.contextId,
            kind: "task",
            status: { state: "completed", timestamp: new Date().toISOString() },
            history: [
              {
                kind: "message",
                role: "user",
                parts: [{ kind: "text", text: t.input }],
                message_id: crypto.randomUUID(),
                task_id: taskId,
                context_id: t.contextId,
              },
            ],
            artifacts: [
              {
                artifact_id: crypto.randomUUID(),
                name: "result",
                parts: [{ kind: "text", text: cfg.respond(t.input) }],
              },
            ],
          },
        }),
      )
      return
    }

    if (rpc.method === "tasks/cancel") {
      const taskId: string | undefined = rpc.params?.taskId ?? rpc.params?.task_id
      if (taskId && tasks.has(taskId)) {
        const t = tasks.get(taskId)!
        t.state = "canceled"
      }
      setJson()
      res.end(
        JSON.stringify({
          jsonrpc: "2.0",
          id: rpc.id,
          result: {
            id: taskId,
            context_id: taskId ? tasks.get(taskId)?.contextId : undefined,
            kind: "task",
            status: { state: "canceled", timestamp: new Date().toISOString() },
          },
        }),
      )
      return
    }

    setJson()
    res.statusCode = 400
    res.end(
      JSON.stringify({
        jsonrpc: "2.0",
        id: rpc.id ?? null,
        error: { code: -32601, message: `method not supported: ${rpc.method}` },
      }),
    )
  })

  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve))
  const port = (server.address() as AddressInfo).port

  return {
    url: `http://127.0.0.1:${port}`,
    port,
    close: () => new Promise((resolve) => server.close(() => resolve())),
  }
}

async function readBody(req: import("http").IncomingMessage): Promise<string> {
  const chunks: Buffer[] = []
  for await (const c of req as AsyncIterable<Buffer>) chunks.push(c)
  return Buffer.concat(chunks).toString("utf8")
}
