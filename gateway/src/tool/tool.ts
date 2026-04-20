import { Effect } from "effect"
import type { z, ZodType } from "zod"

/**
 * Tool abstraction for the gateway planner.
 *
 * Pattern borrowed from OpenCode's `tool/tool.ts` but simpler — no auto
 * telemetry wrapper, no truncation wrapper, no metadata() helper beyond a
 * single status update. Phase 1 tools are dynamic (generated per-session
 * from the External caller's agent catalog), so the surface is minimal.
 */

interface Metadata {
  readonly [key: string]: unknown
}

export interface Context<M extends Metadata = Metadata> {
  readonly sessionId: string
  readonly messageId: string
  readonly agent: string
  readonly callId: string
  readonly abort: AbortSignal
  /** Emit a progress update to the session bus (picked up by SSE projector). */
  readonly metadata: (input: { title?: string; metadata?: M }) => Effect.Effect<void>
  /** Request a user permission decision (Phase 2+ — stub returns allow now). */
  readonly ask?: (input: { permission: string; target?: string }) => Effect.Effect<void, Error>
}

export interface ExecuteResult<M extends Metadata = Metadata> {
  readonly title: string
  readonly output: string
  readonly metadata: M
}

export interface Def<Parameters extends ZodType = ZodType, M extends Metadata = Metadata> {
  readonly id: string
  readonly description: string
  readonly parameters: Parameters
  readonly execute: (args: z.infer<Parameters>, ctx: Context) => Effect.Effect<ExecuteResult<M>, Error>
}

export type DefInit<Parameters extends ZodType = ZodType, M extends Metadata = Metadata> = Omit<
  Def<Parameters, M>,
  "id"
>

export interface Info<Parameters extends ZodType = ZodType, M extends Metadata = Metadata> {
  readonly id: string
  readonly init: () => Effect.Effect<DefInit<Parameters, M>>
}

/**
 * Define a tool statically (most common). Returns an Info that the registry
 * can initialize lazily. Drop-in compatible with OpenCode's Tool.define in
 * how a consumer registers it — the execute signature is narrower (no
 * auto-truncation, no promptOps).
 */
export function define<Parameters extends ZodType, M extends Metadata>(
  id: string,
  init: DefInit<Parameters, M> | (() => Effect.Effect<DefInit<Parameters, M>>),
): Info<Parameters, M> {
  return {
    id,
    init: () => (typeof init === "function" ? init() : Effect.succeed(init)),
  }
}
