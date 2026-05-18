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
import { existsSync, readFileSync, statSync, watchFile, unwatchFile, type Stats } from "node:fs"
import type { Server as HttpsServer } from "node:https"
import tls from "node:tls"
import { Agent } from "undici"

/** Trust bundle = our private step-ca + Node's default Mozilla roots.
 *  Setting `ca` on undici.Agent.connect REPLACES the default CA store;
 *  without this concat, gateway calls to public-CA peers would fail
 *  with UNABLE_TO_VERIFY_LEAF_SIGNATURE. Mirrors withSystemRoots() in
 *  inbox/server/utils.ts. */
function withSystemRoots(caBundle: Buffer): string[] {
  return [...tls.rootCertificates, caBundle.toString("utf8")]
}

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

/**
 * Watch the TLS cert file and swap the live https.Server's secure context
 * in-place when step-ca rotates it (~every 16h).
 *
 * Without this, `getServerTLSOptions()` is consulted exactly once at boot
 * and Node's https.Server keeps serving the old cert forever. When the
 * cert expires the TLS handshake just stops working and operators have
 * to bounce the gateway by hand.
 *
 * `fs.watchFile` polls (1s default) rather than relying on inotify, which
 * matches how step-ca's renewal CLI atomically replaces the file via
 * write-and-rename — inotify would miss the original file's events.
 *
 * Returns a disposer so callers can cancel the watch on shutdown. No-op
 * if no cert env is set (plain HTTP boot — nothing to reload).
 */
export function attachServerCertReloader(server: HttpsServer): () => void {
  const paths = readEnvPaths()
  if (!paths) return () => {}
  let lastMtime = statSync(paths.cert).mtimeMs
  const onChange = (curr: Stats) => {
    if (curr.mtimeMs === lastMtime) return
    lastMtime = curr.mtimeMs
    const opts = getServerTLSOptions()
    if (!opts) return
    try {
      server.setSecureContext(opts)
      console.log(
        `[bindu-gateway] reloaded TLS cert (mtime=${new Date(curr.mtimeMs).toISOString()})`,
      )
    } catch (err) {
      console.error("[bindu-gateway] cert reload failed:", err)
    }
  }
  watchFile(paths.cert, { interval: 60_000 }, onChange)
  return () => unwatchFile(paths.cert, onChange)
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
      ca: withSystemRoots(readFileSync(paths.ca)),
      // Peer cert SANs are DIDs, not hostnames. Identity is enforced
      // at the application layer via X-DID-Signature (auth/resolver.ts
      // builds these for did_signed peers) and the cert chain still
      // has to verify against our private CA bundle (or the Mozilla
      // bundle for public-CA peers — see withSystemRoots above).
      checkServerIdentity: () => undefined,
    },
  })
  cachedPeerDispatcher = { agent, mtimeMs }
  return agent
}
