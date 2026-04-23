import { z } from "zod"
import { CallID, MessageID, PartID, SessionID } from "./schema"

/**
 * Message + Part model for the gateway.
 *
 * Narrower than OpenCode's `message-v2.ts`:
 *   - no Subtask, Compaction, Snapshot, Patch, StepStart/Finish, Retry, or Agent parts
 *   - no LSP attachment shape
 *   - no dual-storage model (SQLite tables)
 *
 * What we keep:
 *   - Text, Tool, File parts
 *   - User, Assistant, System roles
 *   - Usage tracking on assistant messages
 *   - Token and cost totals for audit
 *
 * Wire format: the gateway's `/plan` API doesn't expose these types to
 * External (External gets SSE frames). They're internal to the planner +
 * DB round-trip.
 */

export const TextPart = z.object({
  id: PartID,
  type: z.literal("text"),
  text: z.string(),
  synthetic: z.boolean().optional(),
  time: z
    .object({
      start: z.number(),
      end: z.number().optional(),
    })
    .optional(),
})
export type TextPart = z.infer<typeof TextPart>

export const FilePart = z.object({
  id: PartID,
  type: z.literal("file"),
  mime: z.string(),
  filename: z.string().optional(),
  url: z.string().optional(),
  data: z.string().optional(), // base64
})
export type FilePart = z.infer<typeof FilePart>

export const ToolState = z.discriminatedUnion("status", [
  z.object({
    status: z.literal("pending"),
    input: z.unknown(),
    time: z.object({ start: z.number() }),
  }),
  z.object({
    status: z.literal("running"),
    input: z.unknown(),
    title: z.string().optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
    time: z.object({ start: z.number() }),
  }),
  z.object({
    status: z.literal("completed"),
    input: z.unknown(),
    output: z.string(),
    title: z.string().optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
    time: z.object({ start: z.number(), end: z.number() }),
  }),
  z.object({
    status: z.literal("error"),
    input: z.unknown().optional(),
    error: z.string(),
    time: z.object({ start: z.number(), end: z.number() }),
  }),
])
export type ToolState = z.infer<typeof ToolState>

export const ToolPart = z.object({
  id: PartID,
  type: z.literal("tool"),
  callID: CallID,
  tool: z.string(),
  state: ToolState,
})
export type ToolPart = z.infer<typeof ToolPart>

export const Part = z.discriminatedUnion("type", [TextPart, FilePart, ToolPart])
export type Part = z.infer<typeof Part>

export const UserMessageInfo = z.object({
  id: MessageID,
  sessionID: SessionID,
  role: z.literal("user"),
  time: z.object({ created: z.number() }),
})
export type UserMessageInfo = z.infer<typeof UserMessageInfo>

export const AssistantUsage = z.object({
  input: z.number().default(0),
  output: z.number().default(0),
  total: z.number().default(0),
  cache: z
    .object({
      read: z.number().default(0),
      write: z.number().default(0),
    })
    .default({ read: 0, write: 0 }),
})
export type AssistantUsage = z.infer<typeof AssistantUsage>

export const AssistantMessageInfo = z.object({
  id: MessageID,
  sessionID: SessionID,
  role: z.literal("assistant"),
  modelID: z.string(),
  providerID: z.string(),
  agent: z.string(),
  tokens: AssistantUsage.default({
    input: 0,
    output: 0,
    total: 0,
    cache: { read: 0, write: 0 },
  }),
  time: z.object({ created: z.number(), completed: z.number().optional() }),
  stopReason: z
    .enum(["stop", "length", "tool-calls", "content-filter", "error", "aborted"])
    .optional(),
})
export type AssistantMessageInfo = z.infer<typeof AssistantMessageInfo>

export const MessageInfo = z.discriminatedUnion("role", [UserMessageInfo, AssistantMessageInfo])
export type MessageInfo = z.infer<typeof MessageInfo>

export interface MessageWithParts {
  info: MessageInfo
  parts: Part[]
}

export function asWireRole(role: MessageInfo["role"]): "user" | "assistant" | "system" {
  return role
}

/**
 * Convert our internal Part[] to the AI SDK's ModelMessage shape for sending
 * to the model. Preserves text; flattens tool parts into tool-call + tool-
 * result; drops file parts with no url/data.
 */
export function toModelMessages(messages: MessageWithParts[]): import("ai").ModelMessage[] {
  const out: import("ai").ModelMessage[] = []

  for (const msg of messages) {
    if (msg.info.role === "user") {
      const content: import("ai").UserModelMessage["content"] = []
      for (const p of msg.parts) {
        if (p.type === "text") content.push({ type: "text", text: p.text })
        if (p.type === "file" && (p.url || p.data)) {
          content.push({ type: "image", image: p.url ?? `data:${p.mime};base64,${p.data!}` })
        }
      }
      out.push({ role: "user", content: content.length > 0 ? content : "" })
      continue
    }

    // Assistant
    const toolCalls: import("ai").AssistantModelMessage["content"] = []
    let text = ""
    for (const p of msg.parts) {
      if (p.type === "text") text += p.text
      if (p.type === "tool") {
        toolCalls.push({
          type: "tool-call",
          toolCallId: p.callID,
          toolName: p.tool,
          input: p.state.status !== "error" ? (p.state.input as any) : undefined,
        })
      }
    }
    if (text) toolCalls.unshift({ type: "text", text })
    if (toolCalls.length > 0) out.push({ role: "assistant", content: toolCalls })
    else if (text) out.push({ role: "assistant", content: text })

    // Flatten tool-result messages
    const results: import("ai").ToolModelMessage["content"] = []
    for (const p of msg.parts) {
      if (p.type !== "tool") continue
      if (p.state.status === "completed") {
        results.push({
          type: "tool-result",
          toolCallId: p.callID,
          toolName: p.tool,
          output: { type: "text", value: p.state.output },
        })
      } else if (p.state.status === "error") {
        results.push({
          type: "tool-result",
          toolCallId: p.callID,
          toolName: p.tool,
          output: { type: "error-text", value: p.state.error },
        })
      }
    }
    if (results.length > 0) out.push({ role: "tool", content: results })
  }

  return out
}
