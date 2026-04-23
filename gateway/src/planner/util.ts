import { z } from "zod"
import type { AgentRequest } from "./index"
import type { Task } from "../bindu/protocol/types"

/**
 * Pure helpers used by the planner layer and by direct unit tests. Kept free
 * of Effect/Service deps so they can be tested in isolation.
 */

export function normalizeToolName(raw: string): string {
  return raw.replace(/[^A-Za-z0-9_]/g, "_").slice(0, 80)
}

/**
 * Detect (agent, skill) pairs that would produce colliding tool ids after
 * normalization. Returns the list of collisions (one entry per clashing
 * toolId), or `null` when the catalog is clean.
 *
 * Three real flavors of collision this catches:
 *   1. Two agent entries with the same `name` and same skill `id`.
 *   2. One agent with a duplicated skill `id` in its `skills` array.
 *   3. Non-alphanumerics that flatten to the same normalized id
 *      (e.g., agent "foo.bar" and agent "foo_bar" both normalize to
 *      "call_foo_bar_*"). Rare but real.
 *
 * Silent last-write-wins (the previous behavior in session/prompt.ts's
 * `toolMap` assignment) made the planner invoke whichever entry happened
 * to land last in the agents[] array. A caller that thinks they're
 * load-balancing across two peers sees only one being called — and
 * worse, which one is undefined. Better to reject the request.
 */
export interface ToolIdCollision {
  readonly toolId: string
  readonly entries: ReadonlyArray<{ agentName: string; skillId: string }>
}

export function findDuplicateToolIds(
  agents: ReadonlyArray<AgentRequest>,
): ToolIdCollision[] | null {
  const byToolId = new Map<string, Array<{ agentName: string; skillId: string }>>()
  for (const ag of agents) {
    for (const sk of ag.skills) {
      const toolId = normalizeToolName(`call_${ag.name}_${sk.id}`)
      const bucket = byToolId.get(toolId)
      if (bucket) bucket.push({ agentName: ag.name, skillId: sk.id })
      else byToolId.set(toolId, [{ agentName: ag.name, skillId: sk.id }])
    }
  }
  const collisions: ToolIdCollision[] = []
  for (const [toolId, entries] of byToolId) {
    if (entries.length > 1) collisions.push({ toolId, entries })
  }
  return collisions.length > 0 ? collisions : null
}

/**
 * If ``args`` is the default single-field shape ``{input: "..."}`` (or
 * a bare string), return the inner string so the peer sees a natural
 * user message. Otherwise JSON-stringify — structured skills with
 * richer schemas expect a JSON object on the wire.
 *
 * Exported via the default tool-building path; the peer's Bindu
 * handler ultimately receives ``parts: [{kind: "text", text: <this>}]``.
 * A conversational agent then replies to the text as if it came from
 * the user, which is almost always what the planner intends.
 */
export function extractPlainTextInput(args: unknown): string {
  if (typeof args === "string") return args
  if (
    args !== null &&
    typeof args === "object" &&
    !Array.isArray(args) &&
    Object.keys(args).length === 1 &&
    "input" in args &&
    typeof (args as { input: unknown }).input === "string"
  ) {
    return (args as { input: string }).input
  }
  return JSON.stringify(args)
}

export function extractOutputText(task: Task): string {
  const pieces: string[] = []
  for (const art of task.artifacts ?? []) {
    for (const p of art.parts ?? []) {
      if (p.kind === "text") pieces.push(p.text)
      else if (p.kind === "data") pieces.push(JSON.stringify(p.data))
      else if (p.kind === "file" && p.text) pieces.push(p.text)
    }
  }
  if (pieces.length === 0) return `[task ${task.id} ${task.status.state} — no text output]`
  return pieces.join("\n\n")
}

/**
 * Label the `verified` attribute on the <remote_content> envelope with
 * enough fidelity that the planner LLM can distinguish the four real
 * states verification can produce:
 *
 *   - `"yes"`       — at least one artifact carried a signature AND every
 *                     signed artifact checked out against the pinned DID's
 *                     public key. Strongest claim.
 *   - `"no"`        — at least one signed artifact failed verification.
 *                     Treat the body as definitely-tampered or
 *                     wrong-provenance; the task is also marked `failed`.
 *   - `"unsigned"`  — verification ran, but no artifact had a signature
 *                     attached. Bodies came back; nothing was checked.
 *                     Previously this collapsed into `"yes"` because the
 *                     Bindu client's `signatures.ok` is vacuously true
 *                     when `signed === 0` — misleading. Now it's
 *                     explicit, so the planner can weight the source
 *                     appropriately (e.g., treat as unverified hearsay).
 *   - `"unknown"`   — verification was not attempted. Either
 *                     `trust.verifyDID` was false, no pinned DID was
 *                     supplied, or DID document resolution failed.
 */
export type VerifiedLabel = "yes" | "no" | "unsigned" | "unknown"

export function computeVerifiedLabel(
  signatures: { ok: boolean; signed: number; verified: number; unsigned: number } | null,
): VerifiedLabel {
  if (signatures === null) return "unknown"
  if (!signatures.ok) return "no"
  if (signatures.signed === 0) return "unsigned"
  return "yes"
}

export function wrapRemoteContent(input: {
  agentName: string
  did: string | null
  verified: VerifiedLabel
  body: string
}): string {
  const verified = input.verified
  const didAttr = input.did ? ` did="${escapeAttr(input.did)}"` : ""
  // Scrub nested envelope markers and common injection phrases so a
  // malicious peer can't forge a wrapper inside their own response.
  const scrubbed = input.body
    .replace(/<\/?remote_content[^>]*>/gi, "[stripped]")
    .replace(/\b(ignore (?:all )?previous|disregard earlier)\b/gi, "[stripped]")

  return `<remote_content agent="${escapeAttr(input.agentName)}"${didAttr} verified="${verified}">
${scrubbed}
</remote_content>`
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

/**
 * Minimal JSON Schema → Zod converter. Only the shapes deployed agents
 * actually send — anything exotic falls back to `z.any()`.
 */
export function jsonSchemaToZod(schema: unknown): z.ZodTypeAny | null {
  if (!schema || typeof schema !== "object") return null
  const s = schema as Record<string, any>
  switch (s.type) {
    case "string":
      return z.string()
    case "number":
      return z.number()
    case "integer":
      return z.number().int()
    case "boolean":
      return z.boolean()
    case "array": {
      const items = jsonSchemaToZod(s.items) ?? z.any()
      return z.array(items)
    }
    case "object": {
      const props = (s.properties as Record<string, unknown>) ?? {}
      const required = new Set<string>((s.required as string[]) ?? [])
      const shape: Record<string, z.ZodTypeAny> = {}
      for (const [k, v] of Object.entries(props)) {
        const inner = jsonSchemaToZod(v) ?? z.any()
        shape[k] = required.has(k) ? inner : inner.optional()
      }
      return z.object(shape).passthrough()
    }
    default:
      return z.any()
  }
}
