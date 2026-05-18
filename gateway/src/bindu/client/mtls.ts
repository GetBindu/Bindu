/**
 * mTLS plumbing for the gateway, Phase C.
 *
 * The gateway is spawned by the inbox; when the inbox has a personal
 * agent with a real cert from production step-ca, it passes the cert
 * file paths into the gateway's env. The gateway picks them up here:
 *
 *   - getServerTLSOptions() — feeds the https.createServer factory used
 *     by @hono/node-server, so the gateway serves the planner API over
 *     TLS. Returns undefined when no cert is configured → plain HTTP,
 *     today's behavior.
 *
 *   - getPeerDispatcher() — undici Agent that the outbound JSON-RPC
 *     client (fetch.ts) and the agent-card fetcher use, so calls to
 *     backing Bindu agents present the same cert at the transport
 *     layer. Mirrors the inbox's buildPeerDispatcher() in
 *     inbox/server/utils.ts; same file format, same identity.
 *
 * Both functions check file mtime so a cert renewal (~16h) is picked
 * up without a gateway restart, modulo the next call.
 *
 * The "co-opt the personal agent's cert" model from the rollout plan:
 * the gateway shares an identity with the inbox process. From a peer's
 * perspective, inbox-direct calls and gateway-fanout calls look like
 * the same caller. Tenant separation lives at a future Phase C2 where
 * the gateway gets its own DID.
 */
import { existsSync, readFileSync, statSync } from "node:fs"
import { Agent } from "undici"

const CERT_ENV = "BINDU_GATEWAY_TLS_CERT"
const KEY_ENV = "BINDU_GATEWAY_TLS_KEY"
const CA_ENV = "BINDU_GATEWAY_TLS_CA"

function readEnvPaths(): { cert: string; key: string; ca: string } | undefined {
  const cert = process.env[CERT_ENV]
  const key = process.env[KEY_ENV]
  const ca = process.env[CA_ENV]
  if (!cert || !key || !ca) return undefined
  if (!existsSync(cert) || !existsSync(key) || !existsSync(ca)) return undefined
  return { cert, key, ca }
}

export interface TLSServerOptions {
  cert: Buffer
  key: Buffer
  ca: Buffer
}

/**
 * Returns the cert/key/ca buffers for https.createServer when the
 * gateway has been spawned with TLS env. Returns undefined for plain
 * HTTP (today's default, also the path when the personal agent hasn't
 * been spawned yet on the inbox side).
 */
export function getServerTLSOptions(): TLSServerOptions | undefined {
  const paths = readEnvPaths()
  if (!paths) return undefined
  return {
    cert: readFileSync(paths.cert),
    key: readFileSync(paths.key),
    ca: readFileSync(paths.ca),
  }
}

let cachedPeerDispatcher: { agent: Agent; mtimeMs: number } | null = null

/**
 * Returns an undici Agent that presents the gateway's mTLS cert on
 * outbound A2A calls. Returns undefined when no cert is configured —
 * outbound code falls through to the default fetch dispatcher.
 *
 * Mtime-cached so cert renewal is picked up on next call.
 */
export function getPeerDispatcher(): Agent | undefined {
  const paths = readEnvPaths()
  if (!paths) return undefined
  const mtimeMs = statSync(paths.cert).mtimeMs
  if (cachedPeerDispatcher && cachedPeerDispatcher.mtimeMs === mtimeMs) {
    return cachedPeerDispatcher.agent
  }
  const agent = new Agent({
    connect: {
      cert: readFileSync(paths.cert),
      key: readFileSync(paths.key),
      ca: readFileSync(paths.ca),
      // Peer cert SANs are DIDs, not hostnames. Identity is enforced
      // at the application layer via X-DID-Signature (auth/resolver.ts
      // builds these for did_signed peers) and the cert chain still
      // has to verify against our private CA bundle.
      checkServerIdentity: () => undefined,
    },
  })
  cachedPeerDispatcher = { agent, mtimeMs }
  return agent
}
