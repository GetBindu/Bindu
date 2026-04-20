import { z } from "zod"

/**
 * Bindu A2A wire types.
 *
 * Calibrated against deployed Bindu agents (Phase 0 fixtures at
 * `scripts/dryrun-fixtures/echo-agent/`). Bindu respects A2A 0.3.0 with
 * specific implementation choices captured here.
 *
 * Casing convention: schemas in this file use the CANONICAL camelCase
 * shape. `normalize.ts` handles the wire↔canonical mapping for types that
 * arrive in snake_case (Task, Artifact, HistoryMessage, SkillDetail).
 *
 * Parse permissively throughout — unknown fields on deployed agents are
 * common as Bindu evolves.
 */

// --------------------------------------------------------------------
// Message parts (kind discriminator: "text" | "file" | "data")
// --------------------------------------------------------------------

export const TextPart = z
  .object({
    kind: z.literal("text"),
    text: z.string(),
    embeddings: z.array(z.number()).optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type TextPart = z.infer<typeof TextPart>

export const FilePart = z
  .object({
    kind: z.literal("file"),
    file: z
      .object({
        bytes: z.string().optional(),
        uri: z.string().optional(),
        mimeType: z.string().optional(),
        name: z.string().optional(),
        embeddings: z.array(z.number()).optional(),
      })
      .passthrough(),
    text: z.string().optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type FilePart = z.infer<typeof FilePart>

export const DataPart = z
  .object({
    kind: z.literal("data"),
    data: z.record(z.string(), z.any()),
    text: z.string().optional(),
    embeddings: z.array(z.number()).optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type DataPart = z.infer<typeof DataPart>

export const Part = z.discriminatedUnion("kind", [TextPart, FilePart, DataPart])
export type Part = z.infer<typeof Part>

// --------------------------------------------------------------------
// Message (outbound request shape — camelCase)
// --------------------------------------------------------------------

export const MessageRole = z.enum(["user", "agent", "system"])
export type MessageRole = z.infer<typeof MessageRole>

export const Message = z
  .object({
    messageId: z.string(),
    contextId: z.string(),
    taskId: z.string(),
    kind: z.literal("message"),
    role: MessageRole,
    parts: z.array(Part),
    referenceTaskIds: z.array(z.string()).optional(),
    extensions: z.array(z.string()).optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type Message = z.infer<typeof Message>

// --------------------------------------------------------------------
// Task + TaskStatus (canonical camelCase; HistoryMessage in normalize.ts)
// --------------------------------------------------------------------

export const TaskStateStandard = z.enum([
  "submitted",
  "working",
  "input-required",
  "auth-required",
  "completed",
  "failed",
  "canceled",
  "rejected",
])

/**
 * Any string is accepted to tolerate Bindu extensions (`payment-required`,
 * `suspended`, `negotiation-bid-*`, `pending`, `resumed`, etc.). Clients use
 * `isTerminal`/`needsCallerAction` to classify.
 */
export const TaskState = z.string()
export type TaskState = z.infer<typeof TaskState>

export const TERMINAL_STATES = ["completed", "failed", "canceled", "rejected"] as const
export const NEEDS_ACTION_STATES = [
  "input-required",
  "auth-required",
  "payment-required",
  "trust-verification-required",
] as const

export function isTerminal(state: string): boolean {
  return (TERMINAL_STATES as readonly string[]).includes(state)
}

export function needsCallerAction(state: string): boolean {
  return (NEEDS_ACTION_STATES as readonly string[]).includes(state)
}

export const TaskStatus = z
  .object({
    state: TaskState,
    timestamp: z.string(),
    message: z.any().optional(),
  })
  .passthrough()
export type TaskStatus = z.infer<typeof TaskStatus>

export const Artifact = z
  .object({
    artifactId: z.string(),
    name: z.string().optional(),
    description: z.string().optional(),
    parts: z.array(Part).optional(),
    append: z.boolean().optional(),
    lastChunk: z.boolean().optional(),
    extensions: z.array(z.string()).optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type Artifact = z.infer<typeof Artifact>

/**
 * HistoryMessage — server returns this in `Task.history[]`. The wire is
 * snake_case; callers must `Normalize.fromWire("history-message", raw)`
 * before validation. This schema accepts the CANONICAL camelCase form.
 */
export const HistoryMessage = z
  .object({
    kind: z.literal("message"),
    role: z.union([MessageRole, z.string()]), // some agents return non-standard values
    parts: z.array(Part),
    messageId: z.string(),
    taskId: z.string(),
    contextId: z.string(),
    referenceTaskIds: z.array(z.string()).optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type HistoryMessage = z.infer<typeof HistoryMessage>

export const Task = z
  .object({
    id: z.string(),
    contextId: z.string(),
    kind: z.literal("task"),
    status: TaskStatus,
    history: z.array(HistoryMessage).optional(),
    artifacts: z.array(Artifact).optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type Task = z.infer<typeof Task>

// --------------------------------------------------------------------
// Context (first-class wire type)
// --------------------------------------------------------------------

export const Context = z
  .object({
    contextId: z.string(),
    kind: z.literal("context"),
    tasks: z.array(z.string()).optional(),
    name: z.string().optional(),
    description: z.string().optional(),
    role: z.string(),
    createdAt: z.string(),
    updatedAt: z.string(),
    status: z.enum(["active", "paused", "completed", "archived"]).optional(),
    tags: z.array(z.string()).optional(),
    parentContextId: z.string().optional(),
    referenceContextIds: z.array(z.string()).optional(),
    extensions: z.record(z.string(), z.any()).optional(),
    metadata: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type Context = z.infer<typeof Context>
