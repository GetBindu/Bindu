import { createHash, timingSafeEqual } from "node:crypto"
import { Effect, Stream } from "effect"
import type { Context as HonoContext } from "hono"
import { streamSSE } from "hono/streaming"
import {
  PlanRequest,
  Service as PlannerService,
  findDuplicateToolIds,
  type Interface as PlannerInterface,
  type SessionContext,
} from "../planner"
import { Service as BusService, type Interface as BusInterface } from "../bus"
import { Service as ConfigService, type Config } from "../config"
import { PromptEvent } from "../session/prompt"
import { CompactionEvent } from "../session/compaction"
import { fetchAgentCard } from "../bindu/client/agent-card"
import { getPeerDID } from "../bindu/protocol/identity"
import { z } from "zod"

/**
 * Turn a validation or session-setup error into a JSON body with just the
 * caller-actionable parts. Before this, we dumped `ZodError.message` — a
 * giant JSON blob of internal schema types — into `detail`, which made
 * 400 responses hard to consume and surfaced internal field orderings
 * unnecessarily.
 */
export function formatErrorDetail(e: unknown): {
  detail: string
  issues?: Array<{ path: string; message: string }>
} {
  if (e instanceof z.ZodError) {
    const issues = e.issues.map((i) => ({
      path: i.path.join(".") || "(root)",
      message: i.message,
    }))
    const summary = issues.map((i) => `${i.path}: ${i.message}`).join("; ")
    return { detail: summary, issues }
  }
  return { detail: e instanceof Error ? e.message : String(e) }
}

/**
 * POST /plan — External-facing Hono handler.
 *
 * Flow:
 *   1. Auth + parse.
 *   2. Resolve (create-or-resume) the session BEFORE opening the SSE stream.
 *      This gives us sessionID up-front so bus subscribers can filter by it.
 *      Without the filter, concurrent /plan requests share the global bus
 *      and leak frames into each other's SSE streams.
 *   3. Open SSE, emit `session`, install sessionID-filtered subscribers,
 *      run the plan, then tear subscribers down via AbortSignal-driven
 *      `Stream.interruptWhen` so no PubSub fibers leak past the request.
 *
 * Contract (see gateway/openapi.yaml §paths./plan):
 *   request:  { question, agents[], preferences?, session_id? }
 *   response: SSE stream — session, plan, text.delta*, task.started*,
 *             task.artifact*, task.finished*, final, done
 */

type ConfigInfo = z.infer<typeof Config>

/* --------------------------------------------------------------------------
 * Idempotency layer
 *
 * Two concurrent /plan calls with identical bodies (the canonical example:
 * an inbox operator's draft is resubmitted after a timeout) used to produce
 * two independent sessions with two independent agent fan-outs — every
 * recipient invoked twice, every billing event doubled. The empirical test
 * in run_matrix.sh's `dup-check` mode demonstrates the gap.
 *
 * Process-local map; keyed by an explicit `Idempotency-Key` header when the
 * caller supplies one, otherwise by a sha256 of the raw request body. The
 * entry survives DEDUP_TTL_MS past completion so very-fast resubmits (the
 * common shape of this bug) get the dedup signal instead of a re-run. After
 * the TTL a fresh request with the same body becomes a new session — that's
 * "I meant it this time," not "I clicked submit twice."
 * -------------------------------------------------------------------------- */
const DEDUP_TTL_MS = 5 * 60_000

/** Bound on how long a duplicate caller will wait for the original
 * request's session row to materialize. Longer than typical prepareSession
 * latency (single-digit ms) but short enough that a stalled upstream
 * doesn't pin the duplicate caller indefinitely. */
const DEDUP_SESSION_WAIT_MS = 5_000

/**
 * `sessionID` is a Promise rather than a bare string so a duplicate caller
 * that lands in the same event-loop tick as the original — before the
 * original's prepareSession returns — can still receive a real session id
 * instead of the placeholder empty string. The original resolves the
 * promise once prepareSession completes; if it fails, the promise rejects
 * and the duplicate caller sees an explicit error rather than a stale id.
 */
type DedupEntry = {
  sessionID: Promise<string>
  resolveSessionID: (id: string) => void
  rejectSessionID: (err: Error) => void
  startedAt: number
  completedAt?: number
}

function makeDedupEntry(now: number): DedupEntry {
  let resolveSessionID!: (id: string) => void
  let rejectSessionID!: (err: Error) => void
  const sessionID = new Promise<string>((res, rej) => {
    resolveSessionID = res
    rejectSessionID = rej
  })
  // The promise may settle before any duplicate caller attaches a handler.
  // Without this, an unhandled rejection from a never-observed entry would
  // bubble to the Node process exit handler.
  sessionID.catch(() => {
    /* observed-or-not, swallowing rejection here is intentional */
  })
  return {
    sessionID,
    resolveSessionID,
    rejectSessionID,
    startedAt: now,
  }
}

const dedupMap = new Map<string, DedupEntry>()

/**
 * Wait up to `timeoutMs` for the in-flight original's sessionID. Returns
 * `null` if it doesn't settle in time, or if the underlying prepareSession
 * rejected. Callers treat `null` as "session not yet known" and surface an
 * empty id to the duplicate consumer — better than blocking the SSE stream.
 */
async function waitForSessionID(
  entry: DedupEntry,
  timeoutMs: number,
): Promise<string | null> {
  return Promise.race([
    entry.sessionID.catch(() => null),
    new Promise<null>((res) => setTimeout(() => res(null), timeoutMs)),
  ])
}

function dedupKey(idempHeader: string | undefined, rawBody: string): string {
  if (idempHeader && idempHeader.length > 0) return `hdr:${idempHeader}`
  return `body:${createHash("sha256").update(rawBody).digest("hex")}`
}

function gcDedup(now: number): void {
  for (const [k, v] of dedupMap.entries()) {
    if (v.completedAt !== undefined && now - v.completedAt > DEDUP_TTL_MS) {
      dedupMap.delete(k)
    }
  }
}

function findDedupEntry(key: string, now: number): DedupEntry | null {
  const entry = dedupMap.get(key)
  if (!entry) return null
  if (entry.completedAt !== undefined && now - entry.completedAt > DEDUP_TTL_MS) {
    dedupMap.delete(key)
    return null
  }
  return entry
}

export const buildPlanHandler = Effect.gen(function* () {
  const planner = yield* PlannerService
  const bus = yield* BusService
  const cfg = yield* (yield* ConfigService).get()

  return (c: HonoContext) => handleRequest(c, planner, bus, cfg)
})

async function handleRequest(
  c: HonoContext,
  planner: PlannerInterface,
  bus: BusInterface,
  cfg: ConfigInfo,
): Promise<Response> {
  // 1. Auth (bearer)
  const authConfig = cfg.gateway.auth
  if (authConfig.mode === "bearer") {
    const header = c.req.header("Authorization")
    const token = header?.startsWith("Bearer ") ? header.slice("Bearer ".length) : undefined
    if (!token || !validateBearerToken(token, authConfig.tokens)) {
      return c.json({ error: "unauthorized" }, 401)
    }
  }

  // 2. Parse body. Read raw text first so the idempotency hash keys on the
  //    exact bytes the caller sent — JSON.stringify(parsed) would re-serialize
  //    and could drift across runtimes if any field order changed.
  const rawBody = await c.req.text()
  let request: PlanRequest
  try {
    const body = JSON.parse(rawBody)
    request = PlanRequest.parse(body)
  } catch (e) {
    return c.json({ error: "invalid_request", ...formatErrorDetail(e) }, 400)
  }

  // 2c. Idempotency dedup. Check BEFORE prepareSession so a duplicate doesn't
  //     allocate a fresh session row in Supabase, doesn't enqueue a plan run,
  //     and doesn't fan out a second copy of the request to every recipient.
  //     `Idempotency-Key` header beats body hash: when the caller is explicit
  //     about "this is a retry of submit X", honor it (covers cases where two
  //     resubmits have small inconsequential differences like a re-stamped
  //     `session_id`).
  const idempKey = dedupKey(c.req.header("Idempotency-Key"), rawBody)
  const now = Date.now()
  gcDedup(now)
  const existing = findDedupEntry(idempKey, now)
  if (existing) {
    // Block briefly on the in-flight original's sessionID so the duplicate
    // consumer receives a real id (not the empty placeholder from the
    // same-event-loop-tick race). The original normally resolves it within
    // single-digit milliseconds — well under DEDUP_SESSION_WAIT_MS.
    const resolvedSessionID = await waitForSessionID(
      existing,
      DEDUP_SESSION_WAIT_MS,
    )
    const sessionID = resolvedSessionID ?? ""
    return streamSSE(c, async (stream) => {
      await stream.writeSSE({
        event: "session",
        data: JSON.stringify({
          session_id: sessionID,
          external_session_id: request.session_id ?? null,
          created: false,
        }),
      })
      await stream.writeSSE({
        event: "duplicate",
        data: JSON.stringify({
          session_id: sessionID,
          in_flight: existing.completedAt === undefined,
          message:
            existing.completedAt === undefined
              ? "Plan with identical body is in flight; not re-running."
              : "Plan with identical body recently completed (within idempotency TTL).",
        }),
      })
      await stream.writeSSE({ event: "done", data: "{}" })
    })
  }
  // Register before prepareSession to close the check-and-set race. Two
  // requests landing in the same event-loop tick would otherwise both see
  // no entry; the set is synchronous so whichever runs second loses.
  const dedupEntry = makeDedupEntry(now)
  dedupMap.set(idempKey, dedupEntry)

  // 2a. Reject catalogs that would produce colliding tool ids — silent
  //     last-write-wins in the AI SDK's toolMap was masking caller bugs
  //     (two entries with the same agent name + skill id, or underscores
  //     vs dots in agent names flattening to the same normalized id).
  //     The caller needs to know; give them a clean 400.
  const collisions = findDuplicateToolIds(request.agents)
  if (collisions) {
    const detail = collisions
      .map(
        (c) =>
          `toolId "${c.toolId}" produced by: ${c.entries
            .map((e) => `${e.agentName}/${e.skillId}`)
            .join(", ")}`,
      )
      .join("; ")
    return c.json(
      {
        error: "invalid_request",
        detail: `agents catalog has colliding tool ids — ${detail}`,
      },
      400,
    )
  }

  // 2b. Pre-fetch each peer's AgentCard in parallel (total ≤2s budget)
  //     so we can surface observed DIDs in SSE even when the caller
  //     didn't pin one. Results are cached in fetchAgentCard's
  //     per-process Map — the Bindu client's downstream runCall will
  //     hit the same cache for free. Failures don't block: individual
  //     peer AgentCards default to "not observed", `agent_did` stays
  //     null for that peer.
  const observedByName = new Map<string, string>()
  {
    const discoveryBudget = 2000
    const ac = new AbortController()
    const timer = setTimeout(() => ac.abort(), discoveryBudget)
    try {
      await Promise.allSettled(
        request.agents.map(async (ag) => {
          const card = await fetchAgentCard(ag.endpoint, {
            signal: ac.signal,
            timeoutMs: discoveryBudget,
          })
          if (!card) return
          const did = getPeerDID(card)
          if (did) observedByName.set(ag.name, did)
        }),
      )
    } finally {
      clearTimeout(timer)
    }
  }

  // 3. Resolve session BEFORE opening SSE — required so subscribers can
  //    filter events by sessionID. Any failure here returns plain JSON.
  let sessionCtx: SessionContext
  try {
    sessionCtx = await Effect.runPromise(planner.prepareSession(request))
  } catch (e) {
    // Free the dedup slot so the caller can legitimately retry. Without
    // this, the first attempt's failure would shadow the dedup map and
    // block every retry within the TTL window. Reject the in-flight
    // sessionID promise too so any concurrent duplicate caller breaks
    // out of its waitForSessionID instead of timing out at the 5s bound.
    dedupEntry.rejectSessionID(e instanceof Error ? e : new Error(String(e)))
    dedupMap.delete(idempKey)
    return c.json({ error: "session_failed", ...formatErrorDetail(e) }, 500)
  }
  // Resolve the in-flight sessionID promise so any concurrent duplicate
  // caller awaiting it receives the real id.
  dedupEntry.resolveSessionID(sessionCtx.sessionID)

  // 4. SSE response
  return streamSSE(c, async (stream) => {
    const ac = new AbortController()
    c.req.raw.signal?.addEventListener("abort", () => ac.abort(), { once: true })

    // Filter events to THIS session only. Without this filter, concurrent
    // /plan requests share the global bus and every subscriber receives
    // every other request's frames.
    const ownEvent = <P extends { sessionID: string }>(
      src: Stream.Stream<{ type: string; properties: P }>,
    ) => src.pipe(Stream.filter((e) => e.properties.sessionID === sessionCtx.sessionID))

    // Emit `session` first so clients can correlate every subsequent frame
    // to the right session row.
    await stream.writeSSE({
      event: "session",
      data: JSON.stringify({
        session_id: sessionCtx.sessionID,
        external_session_id: sessionCtx.externalSessionID,
        created: !sessionCtx.existing,
      }),
    })

    // Install subscribers BEFORE runPlan publishes, so we don't miss the
    // first event. Each reader is tied to `ac.signal` and terminates when
    // the request ends.
    spawnReader(ac.signal, ownEvent(bus.subscribe(PromptEvent.Started)), async (evt) => {
      await stream.writeSSE({
        event: "plan",
        data: JSON.stringify({
          plan_id: evt.properties.messageID,
          session_id: evt.properties.sessionID,
        }),
      })
    })

    spawnReader(ac.signal, ownEvent(bus.subscribe(PromptEvent.TextDelta)), async (evt) => {
      await stream.writeSSE({
        event: "text.delta",
        data: JSON.stringify({
          session_id: evt.properties.sessionID,
          part_id: evt.properties.partID,
          delta: evt.properties.delta,
        }),
      })
    })

    spawnReader(ac.signal, ownEvent(bus.subscribe(PromptEvent.ToolCallStart)), async (evt) => {
      const agentName = parseAgentFromTool(evt.properties.tool)
      // Resolve the peer's DID with provenance. Pinned wins over
      // observed (the caller vouched; observed is self-reported).
      // Emitted on every task.* frame so SSE consumers can partition
      // by `agent_did_source` if they only trust pinned claims.
      const agentId = findAgentDID(request, observedByName, agentName)
      await stream.writeSSE({
        event: "task.started",
        data: JSON.stringify({
          task_id: evt.properties.callID,
          agent: agentName,
          agent_did: agentId.did,
          agent_did_source: agentId.source,
          skill: parseSkillFromTool(evt.properties.tool),
          input: evt.properties.input,
        }),
      })
    })

    spawnReader(ac.signal, ownEvent(bus.subscribe(PromptEvent.ToolCallEnd)), async (evt) => {
      const agentName = parseAgentFromTool(evt.properties.tool)
      // Only attach `signatures` when the tool explicitly reported a
      // verification outcome. A `null` here means the tool ran
      // verification but skipped (no pinnedDID, or DID doc resolution
      // failed) — still worth surfacing so operators can tell
      // "skipped" apart from "not attempted" (the latter is absence).
      const sigField =
        evt.properties.signatures !== undefined
          ? { signatures: evt.properties.signatures }
          : {}
      const agentId = findAgentDID(request, observedByName, agentName)
      await stream.writeSSE({
        event: "task.artifact",
        data: JSON.stringify({
          task_id: evt.properties.callID,
          agent: agentName,
          agent_did: agentId.did,
          agent_did_source: agentId.source,
          content: evt.properties.output,
          title: evt.properties.title,
          ...sigField,
        }),
      })
      await stream.writeSSE({
        event: "task.finished",
        data: JSON.stringify({
          task_id: evt.properties.callID,
          agent: agentName,
          agent_did: agentId.did,
          agent_did_source: agentId.source,
          state: evt.properties.error ? "failed" : "completed",
          ...(evt.properties.error ? { error: evt.properties.error } : {}),
          ...sigField,
        }),
      })
    })

    spawnReader(ac.signal, ownEvent(bus.subscribe(PromptEvent.Finished)), async (evt) => {
      await stream.writeSSE({
        event: "final",
        data: JSON.stringify({
          session_id: evt.properties.sessionID,
          stop_reason: evt.properties.stopReason,
          usage: evt.properties.usage,
        }),
      })
    })

    // Path A — compaction summary sidechannel. When the planner's
    // compaction layer summarises an overflowing history, it publishes
    // CompactionEvent.Summary on the bus. We forward it to the client
    // here so the client can persist the summary locally and send it
    // back as `prior_summary` on the next /plan call. That loop is how
    // a stateless gateway preserves long-running session context across
    // requests without owning the durable store.
    spawnReader(ac.signal, ownEvent(bus.subscribe(CompactionEvent.Summary)), async (evt) => {
      await stream.writeSSE({
        event: "compaction-summary",
        data: JSON.stringify({
          session_id: evt.properties.sessionID,
          summary: evt.properties.summary,
          tokens_before: evt.properties.tokensBefore,
          tokens_after: evt.properties.tokensAfter,
          messages_compacted: evt.properties.messagesCompactedCount,
        }),
      })
    })

    // 5. Run the plan (events fire into the subscribers above)
    try {
      await Effect.runPromise(planner.runPlan(sessionCtx, request, { abort: ac.signal }))
    } catch (e) {
      await stream.writeSSE({
        event: "error",
        data: JSON.stringify({ message: (e as Error).message }),
      })
    } finally {
      // Aborting terminates every spawnReader fiber via Stream.interruptWhen,
      // so no PubSub subscriptions leak past this request.
      ac.abort()
      await stream.writeSSE({ event: "done", data: "{}" })
      // Mark the dedup slot as completed. Subsequent identical bodies inside
      // DEDUP_TTL_MS see this as "recently completed" and get the dup signal;
      // beyond the TTL the entry is garbage-collected and a fresh body starts
      // a new session.
      dedupEntry.completedAt = Date.now()
    }
  })
}

/**
 * Bridge an AbortSignal into an Effect that resolves when the signal fires.
 * Used as the trigger for `Stream.interruptWhen` so reader fibers terminate
 * (rather than just go silent) when the /plan request ends.
 */
function abortEffect(signal: AbortSignal): Effect.Effect<void> {
  return Effect.callback<void>((resume) => {
    if (signal.aborted) {
      resume(Effect.void)
      return
    }
    const handler = () => resume(Effect.void)
    signal.addEventListener("abort", handler, { once: true })
    return Effect.sync(() => signal.removeEventListener("abort", handler))
  })
}

function spawnReader<T>(
  signal: AbortSignal,
  source: Stream.Stream<T>,
  cb: (evt: T) => Promise<void>,
): void {
  void Effect.runPromise(
    Stream.runForEach(
      source.pipe(Stream.interruptWhen(abortEffect(signal))),
      (evt) =>
        Effect.promise(async () => {
          if (signal.aborted) return
          try {
            await cb(evt)
          } catch {
            /* swallow — one write failure shouldn't kill the plan */
          }
        }),
    ),
  ).catch(() => {
    /* stream shut down */
  })
}

/**
 * Constant-time bearer-token validator.
 *
 * `Array.prototype.includes` calls `===` which short-circuits on the
 * first mismatching byte; the time difference is observable from the
 * network and lets an attacker recover the token byte-by-byte via
 * statistical sampling. Additionally, iterating the tokens list with a
 * short-circuiting match would leak WHICH token in the list was a
 * prefix of the guess.
 *
 * Defenses in order:
 *   1. Hash both sides to SHA-256 so inputs are ALWAYS 32 bytes —
 *      this removes the length leak and lets timingSafeEqual run
 *      without throwing on unequal-length buffers.
 *   2. Run timingSafeEqual against every configured token, even after
 *      a match — total time becomes O(tokens.length) regardless of
 *      which entry matched (or whether none did).
 *   3. OR the results into a single boolean at the end.
 */
export function validateBearerToken(provided: string, validTokens: readonly string[]): boolean {
  if (validTokens.length === 0) return false
  const providedHash = createHash("sha256").update(provided, "utf8").digest()
  let matched = false
  for (const valid of validTokens) {
    const validHash = createHash("sha256").update(valid, "utf8").digest()
    // Do the compare for EVERY entry (no early return) so total time
    // depends only on tokens.length, never on which token matched.
    if (timingSafeEqual(providedHash, validHash)) matched = true
  }
  return matched
}

function parseAgentFromTool(toolId: string): string {
  const m = toolId.match(/^call_(.+?)_(.+)$/)
  return m?.[1] ?? toolId
}

function parseSkillFromTool(toolId: string): string {
  const m = toolId.match(/^call_(.+?)_(.+)$/)
  return m?.[2] ?? ""
}

/** Shape returned by findAgentDID — keeps DID + provenance together
 *  so every SSE frame can emit both without re-running the lookup. */
export interface AgentDIDResolution {
  readonly did: string | null
  readonly source: "pinned" | "observed" | null
}

/**
 * Resolve a peer's DID with provenance, in precedence order:
 *
 *   1. ``trust.pinnedDID`` from the /plan request catalog — the caller
 *      explicitly declared which DID they expect. Strongest claim.
 *   2. Observed DID from the peer's AgentCard (fetched upfront during
 *      /plan setup, keyed by agent name) — the peer self-reports this
 *      identity at /.well-known/agent.json. Weaker: an impostor can
 *      advertise any DID they like unless signature verification is on.
 *   3. ``null`` — neither path resolved. Consumer can still identify
 *      the peer by name for display; cryptographic identity is
 *      unknown.
 *
 * The ``source`` field lets SSE consumers decide which guarantee they
 * need. A consumer building an audit log of "calls made to peer X"
 * might accept ``observed`` (human-readable correlation); a compliance
 * gate might reject anything other than ``pinned``.
 */
export function findAgentDID(
  request: PlanRequest,
  observedByName: Map<string, string>,
  agentName: string,
): AgentDIDResolution {
  const entry = request.agents.find((a) => a.name === agentName)
  const pinned = entry?.trust?.pinnedDID
  if (pinned) return { did: pinned, source: "pinned" }
  const observed = observedByName.get(agentName)
  if (observed) return { did: observed, source: "observed" }
  return { did: null, source: null }
}
