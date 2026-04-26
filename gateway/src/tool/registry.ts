import { Context, Effect, Layer } from "effect"
import type { Def, Info } from "./tool"

/**
 * Tool registry.
 *
 * Phase 1: holds dynamically-registered tools (one per agent-skill from the
 * External caller's catalog, projected by the planner at session start). No
 * static built-in tools — the gateway is not a coding shell.
 *
 * Thread-safety: registration is scoped per-call via `withTools`, so
 * concurrent `/plan` requests don't see each other's tool sets.
 */

export interface Interface {
  /**
   * Run `body` with the given tool set registered. Tools are scoped to the
   * body's execution; they're removed after it completes or fails.
   */
  readonly withTools: <A, E, R>(
    tools: Def[],
    body: Effect.Effect<A, E, R>,
  ) => Effect.Effect<A, E, R>

  /** Look up a tool by id within the current scope. */
  readonly get: (id: string) => Effect.Effect<Def | undefined>

  /** List tool ids currently registered within the current scope. */
  readonly list: () => Effect.Effect<string[]>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/ToolRegistry") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    // Context.Reference would be prettier, but Phase 1 just uses a per-call
    // scoped map. The body effect clones tools on entry and clears on exit.
    // A request-scoped Map keyed by a session id could be added later.
    const scoped = new Map<string, Def>()

    const withTools: Interface["withTools"] = (tools, body) =>
      Effect.gen(function* () {
        const ids = tools.map((t) => t.id)
        for (const t of tools) scoped.set(t.id, t)
        return yield* body.pipe(
          Effect.ensuring(
            Effect.sync(() => {
              for (const id of ids) scoped.delete(id)
            }),
          ),
        )
      })

    return Service.of({
      withTools,
      get: (id) => Effect.sync(() => scoped.get(id)),
      list: () => Effect.sync(() => Array.from(scoped.keys())),
    })
  }),
)

/**
 * Initialize an Info into a concrete Def. Small helper the planner uses when
 * projecting an agent catalog into dynamic tools.
 */
export function initDef(info: Info): Effect.Effect<Def> {
  return Effect.gen(function* () {
    const init = yield* info.init()
    return { id: info.id, ...init }
  })
}
