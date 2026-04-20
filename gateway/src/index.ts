import "./bindu/identity" // bootstrap ed25519 sha512 hook FIRST
import { Effect, Layer, ManagedRuntime } from "effect"
import { serve } from "@hono/node-server"
import { Hono } from "hono"
import * as Config from "./config"
import * as Bus from "./bus"
import * as Auth from "./auth"
import * as DB from "./db"
import * as Permission from "./permission"
import * as Provider from "./provider"
import * as Recipe from "./recipe"
import * as Agent from "./agent"
import * as Session from "./session"
import * as SessionCompaction from "./session/compaction"
import * as SessionRevert from "./session/revert"
import * as SessionPrompt from "./session/prompt"
import * as ToolRegistry from "./tool/registry"
import * as BinduClient from "./bindu/client"
import * as Server from "./server"
import * as Planner from "./planner"
import { buildPlanHandler } from "./api/plan-route"
import { buildHealthHandler } from "./api/health-route"
import { buildDidHandler } from "./api/did-route"
import {
  loadLocalIdentity,
  type LocalIdentity,
} from "./bindu/identity/local"
import {
  deriveClientSecret,
  ensureHydraClient,
} from "./bindu/identity/hydra-admin"
import {
  createTokenProvider,
  type TokenProvider,
} from "./bindu/identity/hydra-token"

/**
 * Bindu Gateway boot.
 *
 * Composes all services into one Layer, builds a ManagedRuntime, wires the
 * Hono routes onto the server, binds a port, and exports a `shutdown`
 * function for graceful restarts.
 *
 * Import order matters once: `./bindu/identity` runs the ed25519 sha512
 * bootstrap before anything else tries to verify a signature.
 */

// Layered bottom-up. Each `provideMerge` produces a layer that both
// *provides* the services it wires AND exposes them to outer layers.
//
// The composition is wrapped in a factory so the gateway's DID
// identity (loaded from env at boot) can be injected into the
// BinduClient layer. Peers configured with auth.type=did_signed use
// this identity's private key to sign outbound bodies.

function buildAppLayer(
  identity: LocalIdentity | undefined,
  tokenProvider: TokenProvider | undefined,
) {
  // Level 1 — zero-dependency services
  const level1 = Layer.mergeAll(
    Config.layer,
    Bus.layer,
    Auth.layer,
    Permission.layer,
    ToolRegistry.layer,
    BinduClient.makeLayer(identity, tokenProvider),
    Recipe.defaultLayer,
  )

  // Level 2 — need Config (implicitly resolved by provideMerge)
  const level2 = Layer.mergeAll(
    DB.layer,
    Provider.layer,
    Agent.layer(),
    Server.layer,
  ).pipe(Layer.provideMerge(level1))

  // Level 3 — Session needs DB; Revert needs DB
  const level3 = Layer.mergeAll(Session.layer, SessionRevert.layer).pipe(
    Layer.provideMerge(level2),
  )

  // Level 4 — Compaction needs Session + DB + Provider
  const level4 = SessionCompaction.layer.pipe(Layer.provideMerge(level3))

  // Level 5 — Prompt needs Session, Agent, Config, Registry, Bus, Provider, Permission
  const level5 = SessionPrompt.layer.pipe(Layer.provideMerge(level4))

  // Level 6 — Planner needs everything from below
  return Planner.layer.pipe(Layer.provideMerge(level5))
}

/**
 * Default export kept for backward compat — a layer built without
 * a DID identity or token provider. did_signed peers will fail at
 * call time with a clear error pointing at BINDU_GATEWAY_DID_SEED.
 */
export const appLayer = buildAppLayer(undefined, undefined)

/**
 * Load the gateway's DID identity from environment if all required
 * pieces are present. Returns ``undefined`` when identity is not
 * configured — the gateway then runs in its pre-DID mode (talking
 * only to ``none`` / ``bearer`` / ``bearer_env`` peers).
 *
 * Required env vars (all three must be set):
 *
 *   - ``BINDU_GATEWAY_DID_SEED`` — 32-byte Ed25519 seed, base64
 *   - ``BINDU_GATEWAY_AUTHOR``   — author identifier (typically email)
 *   - ``BINDU_GATEWAY_NAME``     — short gateway name
 *
 * Throws if the seed env var IS set but malformed (wrong length, bad
 * base64) — a misconfigured gateway should fail fast at boot, not
 * three layers into a peer call.
 */
export function tryLoadIdentity(): LocalIdentity | undefined {
  const author = process.env.BINDU_GATEWAY_AUTHOR
  const name = process.env.BINDU_GATEWAY_NAME
  const hasSeed = Boolean(process.env.BINDU_GATEWAY_DID_SEED)

  if (!hasSeed && !author && !name) return undefined

  if (!hasSeed || !author || !name) {
    throw new Error(
      "Partial DID identity config — set all three or none: " +
        "BINDU_GATEWAY_DID_SEED, BINDU_GATEWAY_AUTHOR, BINDU_GATEWAY_NAME. " +
        `Got: seed=${hasSeed ? "set" : "missing"}, author=${author ? "set" : "missing"}, name=${name ? "set" : "missing"}`,
    )
  }

  return loadLocalIdentity({ author, name })
}

const DEFAULT_SCOPES = ["openid", "offline", "agent:read", "agent:write"]

/**
 * Auto-register the gateway with Hydra (if configured) and spin
 * up a TokenProvider for outbound did_signed peer calls.
 *
 * Contract:
 *
 *   * Requires ``identity`` (the gateway's DID) — returns undefined
 *     if no identity was loaded, since there's nothing to register.
 *   * Reads three optional env vars:
 *
 *       BINDU_GATEWAY_HYDRA_ADMIN_URL   (e.g. http://hydra:4445)
 *       BINDU_GATEWAY_HYDRA_TOKEN_URL   (e.g. http://hydra:4444/oauth2/token)
 *       BINDU_GATEWAY_HYDRA_SCOPE       (space-separated; default:
 *                                        "openid offline agent:read agent:write")
 *
 *   * If BOTH URLs are set: registers with Hydra (idempotent) and
 *     returns a TokenProvider.
 *   * If NEITHER is set: returns undefined. did_signed peers must
 *     then carry a tokenEnvVar or fail at call time.
 *   * If only one is set: throws a clear error. Partial config is
 *     the worst of all worlds.
 *
 * Blocks boot until registration completes — if the admin API is
 * unreachable at boot, we want to fail fast rather than discover
 * the problem on the first peer call.
 */
export async function setupHydraIntegration(
  identity: LocalIdentity,
): Promise<TokenProvider | undefined> {
  const adminUrl = process.env.BINDU_GATEWAY_HYDRA_ADMIN_URL
  const tokenUrl = process.env.BINDU_GATEWAY_HYDRA_TOKEN_URL
  const scopeStr = process.env.BINDU_GATEWAY_HYDRA_SCOPE

  if (!adminUrl && !tokenUrl) return undefined

  if (!adminUrl || !tokenUrl) {
    throw new Error(
      "Partial Hydra config — set both or neither: " +
        "BINDU_GATEWAY_HYDRA_ADMIN_URL, BINDU_GATEWAY_HYDRA_TOKEN_URL. " +
        `Got: admin=${adminUrl ? "set" : "missing"}, token=${tokenUrl ? "set" : "missing"}`,
    )
  }

  const scope = scopeStr ? scopeStr.split(/\s+/).filter(Boolean) : DEFAULT_SCOPES

  // Re-derive the seed here (not pulled from identity for security —
  // identity doesn't expose raw seed bytes). Safe because the env
  // var was already loaded by loadLocalIdentity.
  const seedB64 = process.env.BINDU_GATEWAY_DID_SEED!
  const seed = new Uint8Array(Buffer.from(seedB64, "base64"))
  const clientSecret = deriveClientSecret(seed)

  console.log(`[bindu-gateway] registering with Hydra at ${adminUrl}...`)
  await ensureHydraClient({
    adminUrl,
    did: identity.did,
    clientName: process.env.BINDU_GATEWAY_NAME ?? "gateway",
    publicKeyBase58: identity.publicKeyBase58,
    clientSecret,
    scope,
  })
  console.log(`[bindu-gateway] Hydra registration confirmed for ${identity.did}`)

  return createTokenProvider({
    tokenUrl,
    clientId: identity.did,
    clientSecret,
    scope,
  })
}

export async function main(): Promise<{ close: () => Promise<void> }> {
  const identity = tryLoadIdentity()
  if (identity) {
    console.log(`[bindu-gateway] DID identity loaded: ${identity.did}`)
    console.log(
      `[bindu-gateway] public key (base58): ${identity.publicKeyBase58}`,
    )
  } else {
    console.log(
      `[bindu-gateway] no DID identity configured (set BINDU_GATEWAY_DID_SEED, ` +
        `_AUTHOR, _NAME to enable did_signed peer auth)`,
    )
  }

  const tokenProvider = identity
    ? await setupHydraIntegration(identity)
    : undefined
  if (identity && !tokenProvider) {
    console.log(
      `[bindu-gateway] Hydra integration not configured — did_signed peers ` +
        `must each set tokenEnvVar. Set BINDU_GATEWAY_HYDRA_ADMIN_URL + ` +
        `_TOKEN_URL to auto-register and auto-acquire tokens.`,
    )
  }

  const runtime = ManagedRuntime.make(buildAppLayer(identity, tokenProvider))

  const cfg = await runtime.runPromise(
    Effect.gen(function* () {
      const c = yield* Config.Service
      return yield* c.get()
    }),
  )

  const planHandler = await runtime.runPromise(buildPlanHandler)
  // `hydraIntegrated` surfaces on /health so operators can see at a glance
  // whether did_signed peers can auto-acquire tokens.
  const healthHandler = await runtime.runPromise(
    buildHealthHandler(identity, tokenProvider !== undefined),
  )

  const app: Hono = await runtime.runPromise(
    Effect.gen(function* () {
      const s = yield* Server.Service
      return s.app
    }),
  )

  app.get("/health", healthHandler)
  app.post("/plan", planHandler)

  // Self-publish the gateway's DID document so A2A peers can resolve
  // ``did:bindu:<gateway>`` to its Ed25519 public key without needing
  // Hydra admin access. Only registered when an identity is loaded —
  // a gateway without a DID has nothing to publish here, and a 404
  // correctly says so.
  if (identity) {
    app.get("/.well-known/did.json", buildDidHandler(identity))
    console.log(
      `[bindu-gateway] publishing DID document at /.well-known/did.json`,
    )
  }

  const { port, hostname } = cfg.gateway.server
  const httpServer = serve({ fetch: app.fetch, port, hostname })

  console.log(`[bindu-gateway] listening on http://${hostname}:${port}`)
  console.log(`[bindu-gateway] session mode: ${cfg.gateway.session.mode}`)

  return {
    close: async () => {
      httpServer.close()
      await runtime.dispose()
    },
  }
}

// ESM entry: only run if invoked directly
const isMain =
  typeof process !== "undefined" && process.argv[1]?.endsWith("/index.ts") // tsx/bun
if (isMain) {
  main().catch((e) => {
    console.error("[bindu-gateway] boot failed:", e)
    process.exit(1)
  })
}
