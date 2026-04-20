import { Hono } from "hono"
import { Context, Effect, Layer } from "effect"
import { Service as ConfigService } from "../config"

/**
 * Hono application factory.
 *
 * Routes:
 *   GET  /health                  — liveness + basic version info
 *   GET  /.well-known/did.json    — self-published DID doc, when a gateway
 *                                   identity is loaded (api/did-route.ts)
 *   POST /plan                    — wired in Day 9 (api/plan-route.ts)
 *   GET  /plan/:sid/...           — Phase 2 resume / replay
 *
 * This module only provides the app shell + `/health`. Route handlers live
 * in `src/api/` so they can own their own request validation + SSE wiring.
 */

export interface Interface {
  readonly app: Hono
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Server") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const cfg = yield* (yield* ConfigService).get()
    const app = new Hono()

    app.get("/health", (c) =>
      c.json({
        ok: true,
        name: "@bindu/gateway",
        session: cfg.gateway.session.mode,
        supabase: Boolean(cfg.gateway.supabase.url),
      }),
    )

    return Service.of({ app })
  }),
)
