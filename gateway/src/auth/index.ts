import { Context, Effect, Layer } from "effect"
import { existsSync, readFileSync, writeFileSync, mkdirSync, chmodSync } from "fs"
import { dirname, resolve } from "path"
import { homedir } from "os"
import { z } from "zod"

/**
 * Credential store for the gateway.
 *
 * Phase 1: we store credentials we use to call downstream Bindu agents (bearer
 * JWTs passed in via the gateway's config or inline in the /plan request —
 * the inline path is more common, so this store is largely for testing and
 * longer-lived provider API keys).
 *
 * Phase 3 will add DIDAuth + MTLSAuth variants when we expose inbound.
 *
 * Storage: `$XDG_CONFIG_HOME/bindu-gateway/auth.json`, file mode 0o600.
 */

export const BearerAuth = z.object({
  type: z.literal("bearer"),
  token: z.string(),
  metadata: z.record(z.string(), z.string()).optional(),
})

export const ApiKeyAuth = z.object({
  type: z.literal("api"),
  key: z.string(),
  metadata: z.record(z.string(), z.string()).optional(),
})

export const OAuthCredentials = z.object({
  type: z.literal("oauth"),
  accessToken: z.string(),
  refreshToken: z.string().optional(),
  expiresAt: z.number().int().optional(),
})

// Phase 3 additions (kept here so the shape is stable from day 1)
export const DIDAuth = z.object({
  type: z.literal("did"),
  method: z.enum(["bindu", "key"]),
  did: z.string(),
  publicKeyBase58: z.string(),
  privateKeyBase58: z.string(),
  author: z.string().optional(),
  agentName: z.string().optional(),
  agentId: z.string().optional(),
})

export const MTLSAuth = z.object({
  type: z.literal("mtls"),
  certPath: z.string(),
  keyPath: z.string(),
  caPath: z.string().optional(),
})

export const Credential = z.discriminatedUnion("type", [
  BearerAuth,
  ApiKeyAuth,
  OAuthCredentials,
  DIDAuth,
  MTLSAuth,
])
export type Credential = z.infer<typeof Credential>

const Store = z.record(z.string(), Credential)

function authPath(): string {
  const override = process.env.BINDU_GATEWAY_AUTH_FILE
  if (override) return override
  const xdg = process.env.XDG_CONFIG_HOME ?? resolve(homedir(), ".config")
  return resolve(xdg, "bindu-gateway", "auth.json")
}

function readStore(): Record<string, Credential> {
  const p = authPath()
  if (!existsSync(p)) return {}
  const raw = readFileSync(p, "utf8")
  if (!raw.trim()) return {}
  const parsed = Store.safeParse(JSON.parse(raw))
  if (!parsed.success) throw new Error(`auth: invalid store at ${p}: ${parsed.error.message}`)
  return parsed.data
}

function writeStore(store: Record<string, Credential>): void {
  const p = authPath()
  mkdirSync(dirname(p), { recursive: true })
  writeFileSync(p, JSON.stringify(store, null, 2), "utf8")
  try {
    chmodSync(p, 0o600)
  } catch {
    /* best-effort — some filesystems (Windows, some CI) reject chmod */
  }
}

export interface Interface {
  readonly get: (key: string) => Effect.Effect<Credential | undefined>
  readonly set: (key: string, credential: Credential) => Effect.Effect<void, Error>
  readonly remove: (key: string) => Effect.Effect<void, Error>
  readonly all: () => Effect.Effect<Record<string, Credential>>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Auth") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    // Eagerly load at boot. Mutations read-modify-write to stay durable.
    let cache: Record<string, Credential> = yield* Effect.try({
      try: () => readStore(),
      catch: (e) => (e instanceof Error ? e : new Error(String(e))),
    })

    return Service.of({
      get: (key) => Effect.sync(() => cache[key]),

      set: (key, credential) =>
        Effect.try({
          try: () => {
            const parsed = Credential.parse(credential)
            cache = { ...cache, [key]: parsed }
            writeStore(cache)
          },
          catch: (e) => (e instanceof Error ? e : new Error(`auth.set: ${String(e)}`)),
        }),

      remove: (key) =>
        Effect.try({
          try: () => {
            const { [key]: _, ...rest } = cache
            cache = rest
            writeStore(cache)
          },
          catch: (e) => (e instanceof Error ? e : new Error(`auth.remove: ${String(e)}`)),
        }),

      all: () => Effect.sync(() => ({ ...cache })),
    })
  }),
)
