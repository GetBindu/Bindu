import { Context, Effect, Layer } from "effect"
import { createClient, type SupabaseClient } from "@supabase/supabase-js"
import { Service as ConfigService } from "../config"
import type { MessageRow, SessionRow, TaskRow, TaskState } from "./types"

export * from "./types"

/**
 * Supabase DB service for gateway session state.
 *
 * Wraps the supabase-js client behind a narrow Effect interface. All other
 * modules depend on `DB.Service`, never the supabase client directly — this
 * keeps the storage backend swappable (Phase 2 could add an in-memory impl
 * for stateless mode or a direct-postgres impl for leaner deployments).
 */

export interface AppendMessageInput {
  sessionId: string
  role: MessageRow["role"]
  parts: unknown[]
  metadata?: Record<string, unknown>
}

export interface RecordTaskInput {
  sessionId: string
  agentName: string
  skillId?: string
  endpointUrl: string
  remoteTaskId?: string
  remoteContextId?: string
  input?: unknown
  state?: TaskState
}

export interface FinishTaskInput {
  id: string
  state: TaskState
  outputText?: string
  usage?: Record<string, unknown>
  remoteContextId?: string
  /** The peer-assigned task id, known only after the peer responds.
   *  Recorded here so the `remote_task_id` column (and its index) become
   *  usable for debugging, cancel, and reconciliation. */
  remoteTaskId?: string
}

export interface Interface {
  readonly createSession: (input: {
    externalId?: string
    prefs?: Record<string, unknown>
    agentCatalog?: unknown[]
  }) => Effect.Effect<SessionRow, Error>

  readonly getSession: (key: {
    id?: string
    externalId?: string
  }) => Effect.Effect<SessionRow | undefined, Error>

  readonly touchSession: (id: string) => Effect.Effect<void, Error>

  readonly updateSessionCatalog: (id: string, agentCatalog: unknown[]) => Effect.Effect<void, Error>

  readonly appendMessage: (input: AppendMessageInput) => Effect.Effect<MessageRow, Error>

  readonly listMessages: (
    sessionId: string,
    opts?: { limit?: number; includeInactive?: boolean },
  ) => Effect.Effect<MessageRow[], Error>

  readonly recordTask: (input: RecordTaskInput) => Effect.Effect<TaskRow, Error>

  readonly finishTask: (input: FinishTaskInput) => Effect.Effect<void, Error>

  readonly listTasks: (
    sessionId: string,
    opts?: { limit?: number },
  ) => Effect.Effect<TaskRow[], Error>

  /** Exposed for tests / debugging only. Prod code should use the typed methods above. */
  readonly client: () => SupabaseClient
}

export class Service extends Context.Service<Service, Interface>()("@bindu/DB") {}

function fromThrowable<A>(
  fn: () => PromiseLike<{ data: A | null; error: any }>,
  ctx: string,
): Effect.Effect<A, Error> {
  return Effect.tryPromise({
    try: async () => {
      const { data, error } = await Promise.resolve(fn())
      if (error) throw Object.assign(new Error(`${ctx}: ${error.message ?? String(error)}`), { cause: error })
      return data as A
    },
    catch: (e) => (e instanceof Error ? e : new Error(`${ctx}: ${String(e)}`)),
  })
}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const cfg = yield* (yield* ConfigService).get()
    const { url, serviceRoleKey } = cfg.gateway.supabase

    const client: SupabaseClient = createClient(url, serviceRoleKey, {
      auth: { persistSession: false, autoRefreshToken: false },
      db: { schema: cfg.gateway.supabase.schema as any },
    })

    const createSession: Interface["createSession"] = ({ externalId, prefs, agentCatalog }) =>
      fromThrowable(
        () =>
          client
            .from("gateway_sessions")
            .insert({
              external_session_id: externalId ?? null,
              user_prefs: prefs ?? {},
              agent_catalog: agentCatalog ?? [],
            })
            .select()
            .single(),
        "createSession",
      ) as Effect.Effect<SessionRow, Error>

    const getSession: Interface["getSession"] = (key) =>
      Effect.gen(function* () {
        const q = client.from("gateway_sessions").select("*")
        if (key.id) q.eq("id", key.id)
        else if (key.externalId) q.eq("external_session_id", key.externalId)
        else return undefined
        const { data, error } = yield* Effect.promise(() => q.maybeSingle())
        if (error) return yield* Effect.fail(new Error(`getSession: ${error.message}`))
        return (data as SessionRow | null) ?? undefined
      })

    const touchSession: Interface["touchSession"] = (id) =>
      Effect.gen(function* () {
        const { error } = yield* Effect.promise(() =>
          client
            .from("gateway_sessions")
            .update({ last_active_at: new Date().toISOString() })
            .eq("id", id),
        )
        if (error) return yield* Effect.fail(new Error(`touchSession: ${error.message}`))
      })

    const updateSessionCatalog: Interface["updateSessionCatalog"] = (id, agentCatalog) =>
      Effect.gen(function* () {
        const { error } = yield* Effect.promise(() =>
          client
            .from("gateway_sessions")
            .update({
              agent_catalog: agentCatalog,
              last_active_at: new Date().toISOString(),
            })
            .eq("id", id),
        )
        if (error) return yield* Effect.fail(new Error(`updateSessionCatalog: ${error.message}`))
      })

    const appendMessage: Interface["appendMessage"] = ({ sessionId, role, parts, metadata }) =>
      fromThrowable(
        () =>
          client
            .from("gateway_messages")
            .insert({
              session_id: sessionId,
              role,
              parts,
              metadata: metadata ?? {},
            })
            .select()
            .single(),
        "appendMessage",
      ) as Effect.Effect<MessageRow, Error>

    const listMessages: Interface["listMessages"] = (sessionId, opts) =>
      fromThrowable(
        () => {
          let q = client
            .from("gateway_messages")
            .select("*")
            .eq("session_id", sessionId)
            .order("created_at", { ascending: true })
            .limit(opts?.limit ?? 1000)
          // Phase 1: always filter compacted/reverted unless includeInactive is set.
          // Migration 002 adds these columns; running against an un-migrated DB
          // still works because the filters just match all rows (default false).
          if (!opts?.includeInactive) {
            q = q.eq("compacted", false).eq("reverted", false)
          }
          return q.then((r: any) => ({ data: r.data as MessageRow[] | null, error: r.error }))
        },
        "listMessages",
      ) as Effect.Effect<MessageRow[], Error>

    const recordTask: Interface["recordTask"] = (input) =>
      fromThrowable(
        () =>
          client
            .from("gateway_tasks")
            .insert({
              session_id: input.sessionId,
              agent_name: input.agentName,
              skill_id: input.skillId ?? null,
              endpoint_url: input.endpointUrl,
              remote_task_id: input.remoteTaskId ?? null,
              remote_context_id: input.remoteContextId ?? null,
              input: input.input ?? null,
              state: input.state ?? "submitted",
            })
            .select()
            .single(),
        "recordTask",
      ) as Effect.Effect<TaskRow, Error>

    const finishTask: Interface["finishTask"] = ({ id, state, outputText, usage, remoteContextId, remoteTaskId }) =>
      Effect.gen(function* () {
        const patch: Record<string, unknown> = {
          state,
          finished_at: new Date().toISOString(),
        }
        if (outputText !== undefined) patch.output_text = outputText
        if (usage !== undefined) patch.usage = usage
        if (remoteContextId !== undefined) patch.remote_context_id = remoteContextId
        if (remoteTaskId !== undefined) patch.remote_task_id = remoteTaskId
        const { error } = yield* Effect.promise(() =>
          client.from("gateway_tasks").update(patch).eq("id", id),
        )
        if (error) return yield* Effect.fail(new Error(`finishTask: ${error.message}`))
      })

    const listTasks: Interface["listTasks"] = (sessionId, opts) =>
      fromThrowable(
        () =>
          client
            .from("gateway_tasks")
            .select("*")
            .eq("session_id", sessionId)
            .order("started_at", { ascending: true })
            .limit(opts?.limit ?? 1000)
            .then((r: any) => ({ data: r.data as TaskRow[] | null, error: r.error })),
        "listTasks",
      ) as Effect.Effect<TaskRow[], Error>

    return Service.of({
      createSession,
      getSession,
      touchSession,
      updateSessionCatalog,
      appendMessage,
      listMessages,
      recordTask,
      finishTask,
      listTasks,
      client: () => client,
    })
  }),
)
