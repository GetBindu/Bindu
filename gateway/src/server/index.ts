import { Hono } from "hono"
import { Context, Effect, Layer } from "effect"

/**
 * Hono application factory.
 *
 * The shell is deliberately minimal — all routes are built in `src/api/`
 * and mounted from `src/index.ts`, so each route owns its own request
 * validation, SSE wiring, and dependency graph:
 *
 *   POST /plan                    → api/plan-route.ts
 *   GET  /health                  → api/health-route.ts
 *   GET  /.well-known/did.json    → api/did-route.ts (conditional on identity)
 */

export interface Interface {
  readonly app: Hono
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Server") {}

export const layer = Layer.effect(
  Service,
  Effect.sync(() => {
    const app = new Hono()
    return Service.of({ app })
  }),
)
