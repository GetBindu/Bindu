import { AgentCard } from "../protocol/agent-card"

/**
 * Fetch and parse a peer's AgentCard from `/.well-known/agent.json`.
 *
 * Populated via this helper, the `peer.card` field on a PeerDescriptor
 * activates the DID fallback in `maybeVerifySignatures` — when the
 * caller sets `trust.verifyDID: true` but didn't pin a DID, the
 * gateway can recover the peer's published DID from its AgentCard and
 * verify artifacts against the corresponding public key.
 *
 * # Cache
 *
 * Per-process, keyed by peer URL. AgentCards are stable for the life
 * of the peer process; a gateway restart is an acceptable boundary
 * for picking up a rotated identity. Negative results (404, malformed
 * JSON, timeout) are cached too so a flaky peer doesn't cost us one
 * outbound fetch per /plan.
 *
 * # Timeout
 *
 * 2 seconds by default — the fetch blocks the first call to a new
 * peer, so we keep it short. Callers can override via the opts.
 *
 * # Errors become `null`
 *
 * Every failure mode (network error, non-2xx, invalid JSON, schema
 * mismatch, abort) returns `null` rather than throwing. The fallback
 * in maybeVerifySignatures degrades gracefully — null peer.card just
 * means the pinnedDID path is the only option, same behavior as before
 * this module existed. Errors aren't "safety failures" here; they're
 * "couldn't enrich."
 */

const cache = new Map<string, AgentCard | null>()

export interface FetchAgentCardOptions {
  readonly signal?: AbortSignal
  readonly timeoutMs?: number
}

const DEFAULT_TIMEOUT_MS = 2000
const WELL_KNOWN_PATH = "/.well-known/agent.json"

export async function fetchAgentCard(
  peerUrl: string,
  opts: FetchAgentCardOptions = {},
): Promise<AgentCard | null> {
  if (cache.has(peerUrl)) return cache.get(peerUrl) ?? null

  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const ac = new AbortController()
  const timer = setTimeout(() => ac.abort(), timeoutMs)
  const onUpstreamAbort = () => ac.abort()
  opts.signal?.addEventListener("abort", onUpstreamAbort, { once: true })

  try {
    const target = new URL(WELL_KNOWN_PATH, peerUrl).toString()
    const res = await fetch(target, { signal: ac.signal })
    if (!res.ok) {
      cache.set(peerUrl, null)
      return null
    }
    const json = (await res.json()) as unknown
    const parsed = AgentCard.safeParse(json)
    if (!parsed.success) {
      cache.set(peerUrl, null)
      return null
    }
    cache.set(peerUrl, parsed.data)
    return parsed.data
  } catch {
    cache.set(peerUrl, null)
    return null
  } finally {
    clearTimeout(timer)
    opts.signal?.removeEventListener("abort", onUpstreamAbort)
  }
}

/**
 * Reset the AgentCard cache. Only intended for use in tests — production
 * callers have no reason to evict (a gateway restart picks up any
 * identity rotation). Exported on a `__`-prefixed name to signal intent.
 */
export function __resetAgentCardCacheForTests(): void {
  cache.clear()
}
