import { Context, Effect, Layer } from "effect"
import { Config as ConfigSchema } from "./schema"
import { loadConfig } from "./loader"
import type { z } from "zod"

export * from "./schema"

/**
 * Config service — loads once at boot, immutable thereafter.
 *
 * Design: simpler than OpenCode's hierarchical+watched config. The gateway is
 * a backend service; it reloads by restarting. No on-disk mutation path.
 */

export interface Interface {
  readonly get: () => Effect.Effect<z.infer<typeof ConfigSchema>>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Config") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const cfg = yield* Effect.try({
      try: () => loadConfig(),
      catch: (e) => new Error(`Config load failed: ${(e as Error).message}`),
    })

    return Service.of({
      get: () => Effect.succeed(cfg),
    })
  }),
)

export { ConfigSchema as Info }
