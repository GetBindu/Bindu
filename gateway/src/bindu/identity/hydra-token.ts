/**
 * OAuth2 client_credentials token provider for the gateway's DID
 * identity. In-memory cache + proactive refresh so every outbound
 * call to a did_signed peer gets a fresh-enough token without
 * round-tripping Hydra each time.
 *
 * Why here instead of a per-request fetch:
 *
 *   * Latency — Hydra introspection on every call would add tens
 *     of ms to each outbound RPC. Cache hits are free.
 *   * Rate limit — some Hydra deployments throttle /oauth2/token;
 *     exhausting a rate budget during a plan's tool-call fan-out
 *     would cascade into 429s.
 *   * Concurrency — several concurrent outbound calls during the
 *     same plan must not each trigger a separate refresh. The
 *     provider shares a single in-flight promise across callers.
 *
 * Deliberately in-memory only. A persistent cache (disk / Redis)
 * would add complexity without improving the common path — on
 * gateway restart we re-register with Hydra via hydra-admin
 * anyway, so cold-start token fetch is already the expected cost.
 */

export interface TokenProvider {
  /** Returns a fresh access token, fetching from Hydra when the
   *  cache is cold or the cached token is within
   *  ``refreshThresholdSec`` of expiry. Concurrent callers during
   *  a refresh share the same in-flight promise. */
  getToken(): Promise<string>
}

export interface CreateTokenProviderOpts {
  /** Hydra public token endpoint, e.g. http://hydra:4444/oauth2/token */
  tokenUrl: string
  clientId: string
  clientSecret: string
  scope: string[]
  /** Refresh the token when it has less than this many seconds
   *  remaining. Default 30 — long enough to survive a slow plan
   *  turn without expiring mid-request. */
  refreshThresholdSec?: number
  /** Test hook. */
  fetch?: typeof fetch
  /** Clock injection for deterministic tests. Production: Date.now. */
  now?: () => number
}

interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  scope?: string
}

export function createTokenProvider(
  opts: CreateTokenProviderOpts,
): TokenProvider {
  const fetcher = opts.fetch ?? fetch
  const now = opts.now ?? Date.now
  const refreshThresholdMs = (opts.refreshThresholdSec ?? 30) * 1000

  // Cached token state. null = no cached value; ``expiresAtMs`` is
  // an absolute epoch ms, ``refresh at'' is
  // expiresAtMs - refreshThresholdMs.
  let cached: { token: string; expiresAtMs: number } | null = null
  // In-flight fetch. Shared across concurrent callers so we only
  // hit Hydra once per refresh window.
  let inFlight: Promise<string> | null = null

  async function fetchToken(): Promise<string> {
    const body = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: opts.clientId,
      client_secret: opts.clientSecret,
      scope: opts.scope.join(" "),
    })

    const resp = await fetcher(opts.tokenUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
      },
      body: body.toString(),
    })

    if (!resp.ok) {
      const text = await resp.text().catch(() => "")
      throw new Error(
        `Hydra token endpoint returned ${resp.status}: ${text.slice(0, 300)}`,
      )
    }

    const data = (await resp.json()) as TokenResponse
    if (!data.access_token || typeof data.expires_in !== "number") {
      throw new Error(
        `Hydra token response missing access_token or expires_in: ${JSON.stringify(data).slice(0, 300)}`,
      )
    }

    cached = {
      token: data.access_token,
      expiresAtMs: now() + data.expires_in * 1000,
    }
    return data.access_token
  }

  async function getToken(): Promise<string> {
    // Cache hit — return immediately if we have enough runway.
    if (cached && cached.expiresAtMs - now() > refreshThresholdMs) {
      return cached.token
    }

    // Already refreshing — share the in-flight promise.
    if (inFlight) return inFlight

    inFlight = fetchToken().finally(() => {
      inFlight = null
    })
    return inFlight
  }

  return { getToken }
}
