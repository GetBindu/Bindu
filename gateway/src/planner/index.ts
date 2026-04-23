import { Context, Effect, Layer } from "effect"
import { randomUUID } from "crypto"
import { z } from "zod"
import { Service as SessionService, type MessageWithParts } from "../session"
import { Service as SessionPromptService } from "../session/prompt"
import { Service as SessionCompactionService } from "../session/compaction"
import { Service as DBService } from "../db"
import { Service as BusService } from "../bus"
import { Service as BinduClientService } from "../bindu/client"
import { Service as AgentService } from "../agent"
import * as Recipe from "../recipe"
import { buildLoadRecipeTool } from "../tool/recipe"
import type { Def } from "../tool/tool"
import type { PeerDescriptor } from "../bindu/client"
import type { PeerAuth } from "../bindu/auth/resolver"
import type { SessionID } from "../session/schema"
import { buildSkillTool } from "./skill-tool"

/**
 * Planner — turns External's agent catalog into dynamic tools, then runs
 * `SessionPrompt.prompt` with them to answer the user's question.
 *
 * This is the thin layer that adapts a single /plan request into one
 * agent-loop turn. The heavy logic (loop, streaming, tool execution) lives
 * in SessionPrompt; the Bindu network I/O lives in Client. Planner just
 * stitches them together.
 *
 * Module shape:
 *   - this file: schemas + Service + layer (the public API)
 *   - ./skill-tool: the `call_<peer>_<skill>` tool factory
 *   - ./util: pure helpers (name normalization, verified-label logic,
 *     json-schema→zod, <remote_content> envelope)
 *
 * Phase 0 learning applied: peer URL comes from the caller's agent.endpoint,
 * never from AgentCard.url. Caller is the single source of truth for where
 * to reach a given agent.
 */

// Re-export util/skill-tool surface so callers and tests can import from
// `../planner` regardless of the internal file split.
export {
  normalizeToolName,
  findDuplicateToolIds,
  extractPlainTextInput,
  extractOutputText,
  computeVerifiedLabel,
  wrapRemoteContent,
  jsonSchemaToZod,
} from "./util"
export type { ToolIdCollision, VerifiedLabel } from "./util"
export type { BuildToolDeps } from "./skill-tool"

// --------------------------------------------------------------------
// Plan request shape (matches PLAN.md §API)
// --------------------------------------------------------------------

// External /plan API — agent auth descriptor.
//
// Must stay in sync with ``PeerAuth`` in ``src/bindu/auth/resolver.ts``.
// They're two schemas for the same concept: PeerAuthRequest validates
// the incoming /plan request, PeerAuth is the internal shape the peer
// resolver understands. Drift between them causes silent acceptance of
// auth types the transport can't actually execute (or, as happened
// before this comment, the reverse: /plan rejects auth types the
// transport fully supports).
export const PeerAuthRequest = z.discriminatedUnion("type", [
  z.object({ type: z.literal("none") }),
  z.object({ type: z.literal("bearer"), token: z.string() }),
  z.object({ type: z.literal("bearer_env"), envVar: z.string() }),
  z.object({
    type: z.literal("did_signed"),
    // Optional — see PeerAuth in resolver.ts for the full semantics.
    // Omit to use the gateway's auto-acquired Hydra token.
    tokenEnvVar: z.string().optional(),
  }),
])

export const SkillRequest = z.object({
  id: z.string(),
  description: z.string().optional(),
  inputSchema: z.unknown().optional(),
  outputModes: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
})
export type SkillRequest = z.infer<typeof SkillRequest>

export const AgentRequest = z.object({
  name: z.string(),
  endpoint: z.string().url(),
  auth: PeerAuthRequest.optional(),
  trust: z
    .object({
      verifyDID: z.boolean().optional(),
      pinnedDID: z.string().optional(),
    })
    .optional(),
  skills: z.array(SkillRequest).default([]),
})
export type AgentRequest = z.infer<typeof AgentRequest>

// Preferences on /plan — keys match the documented external API shape
// in gateway/openapi.yaml §PlanPreferences: snake_case. An earlier draft
// declared them camelCase (``responseFormat``/``maxHops``/``timeoutMs``/``maxSteps``);
// clients sending docs-compliant ``max_steps`` landed on undefined
// silently via ``.passthrough()``, dropping the cap and falling back
// to ``plannerAgent.steps``. Aligning the schema with the docs fixes
// the silent discard. ``.passthrough()`` stays so forward-compat
// extra keys don't break old clients.
export const PlanPreferences = z
  .object({
    response_format: z.string().optional(),
    max_hops: z.number().int().positive().optional(),
    timeout_ms: z.number().int().positive().optional(),
    max_steps: z.number().int().positive().optional(),
  })
  .partial()
  .passthrough()

export const PlanRequest = z.object({
  // Non-empty — Anthropic (and some other providers) reject an empty
  // user message with a 400 mid-stream, which surfaces to the caller
  // as a vague ``"Provider returned error"``. Validating here gives
  // a clean 400 with ``invalid_request`` at the API boundary instead.
  question: z.string().min(1, "question must be a non-empty string"),
  agents: z.array(AgentRequest).default([]),
  preferences: PlanPreferences.optional(),
  session_id: z.string().optional(),
})
export type PlanRequest = z.infer<typeof PlanRequest>

// --------------------------------------------------------------------
// Planner service
// --------------------------------------------------------------------

/**
 * Session-identity slice of a plan request. Exposed via prepareSession so
 * the /plan SSE handler can learn sessionID BEFORE runPlan starts
 * publishing — required for sessionID-filtered subscribers, which prevent
 * concurrent plans from leaking frames into each other's SSE streams.
 */
export interface SessionContext {
  sessionID: SessionID
  externalSessionID: string | null
  /** true if we resumed an existing row, false if we just created one. */
  existing: boolean
}

export interface RunPlanOutcome {
  message: MessageWithParts
  tasksRecorded: string[]
}

export interface StartPlanOutcome extends RunPlanOutcome {
  sessionID: SessionID
  externalSessionID: string | null
}

export interface Interface {
  /** Resolve (create or resume) the session only. No LLM work, no events. */
  readonly prepareSession: (request: PlanRequest) => Effect.Effect<SessionContext, Error>
  /** Run compaction + the prompt loop against an already-resolved session. */
  readonly runPlan: (
    ctx: SessionContext,
    request: PlanRequest,
    opts?: { abort?: AbortSignal },
  ) => Effect.Effect<RunPlanOutcome, Error>
  /** Convenience: prepareSession + runPlan in one shot. */
  readonly startPlan: (
    request: PlanRequest,
    opts?: { abort?: AbortSignal },
  ) => Effect.Effect<StartPlanOutcome, Error>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Planner") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const sessions = yield* SessionService
    const prompt = yield* SessionPromptService
    const compaction = yield* SessionCompactionService
    const db = yield* DBService
    const bus = yield* BusService
    const client = yield* BinduClientService
    const agents = yield* AgentService
    const recipes = yield* Recipe.Service

    const prepareSession: Interface["prepareSession"] = (request) =>
      Effect.gen(function* () {
        const existing = request.session_id
          ? yield* db.getSession({ externalId: request.session_id })
          : undefined

        const sessionRow = existing
          ? existing
          : yield* sessions.create({
              externalSessionID: request.session_id,
              agentCatalog: request.agents,
            })
        const sessionID = sessionRow.id as unknown as SessionID

        if (existing) {
          yield* db.updateSessionCatalog(sessionID, request.agents)
        }

        return {
          sessionID,
          externalSessionID: sessionRow.external_session_id,
          existing: !!existing,
        }
      })

    const runPlan: Interface["runPlan"] = (ctx, request, opts) =>
      Effect.gen(function* () {
        const plannerAgent = yield* agents.get("planner")
        if (!plannerAgent) {
          return yield* Effect.fail(new Error('planner: no "planner" agent configured'))
        }

        const model = plannerAgent.model ?? "openrouter/anthropic/claude-sonnet-4.6"
        yield* compaction
          .compactIfNeeded({
            sessionID: ctx.sessionID,
            model,
            abortSignal: opts?.abort,
          })
          .pipe(
            Effect.catch((e: Error) =>
              bus.publish(
                { type: "planner.compaction.failed", properties: z.object({ message: z.string() }) } as any,
                { message: e.message } as any,
              ),
            ),
          )

        const contextId = ctx.sessionID
        const tasksRecorded: string[] = []
        const tools: Def[] = []

        for (const ag of request.agents) {
          const peer: PeerDescriptor = {
            name: ag.name,
            url: ag.endpoint,
            auth: ag.auth as PeerAuth | undefined,
            trust: ag.trust,
          }
          for (const sk of ag.skills) {
            tools.push(buildSkillTool(peer, sk, { client, db, contextId, tasksRecorded }))
          }
        }

        // Recipes (progressive-disclosure playbooks) are filtered through
        // the planner agent's permission rules; an empty list means either
        // no recipes on disk or all denied. In either case we skip the
        // system-prompt block and the tool description falls back to
        // "no recipes available" — no noise injected.
        const recipeList = yield* recipes.available(plannerAgent)
        tools.push(buildLoadRecipeTool(recipes, recipeList))
        const recipeSummary =
          recipeList.length > 0 ? Recipe.fmt(recipeList, { verbose: true }) : undefined

        const message = yield* prompt.prompt({
          sessionID: ctx.sessionID,
          agent: "planner",
          parts: [
            {
              id: randomUUID() as any,
              type: "text",
              text: request.question,
              time: { start: Date.now() },
            },
          ],
          tools,
          modelOverride: plannerAgent.model,
          stepsOverride: request.preferences?.max_steps ?? plannerAgent.steps,
          abort: opts?.abort,
          recipeSummary,
        })

        return { message, tasksRecorded }
      })

    const startPlan: Interface["startPlan"] = (request, opts) =>
      Effect.gen(function* () {
        const ctx = yield* prepareSession(request)
        const result = yield* runPlan(ctx, request, opts)
        return {
          sessionID: ctx.sessionID,
          externalSessionID: ctx.externalSessionID,
          message: result.message,
          tasksRecorded: result.tasksRecorded,
        }
      })

    return Service.of({ prepareSession, runPlan, startPlan })
  }),
)
