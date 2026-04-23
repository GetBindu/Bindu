/**
 * Hydra admin API client for the gateway's own OAuth client
 * registration.
 *
 * The gateway registers itself with Hydra on boot so peers can
 * verify it. The registration is idempotent: on restart the gateway
 * re-registers with the same DID as ``client_id`` and the same
 * deterministically-derived ``client_secret``; Hydra either confirms
 * the client exists (200 GET) or creates it (404 → POST).
 *
 * The client_secret is derived from the gateway's seed (see
 * ``deriveClientSecret`` below). This avoids the "where do I persist
 * the OAuth secret" problem — there's no disk state the gateway
 * needs to keep around beyond the seed env var it already requires.
 * Anyone with the seed can compute the secret, but anyone with the
 * seed could already impersonate the gateway by signing as it — the
 * secret adds no new trust boundary, it's just a mechanism for the
 * OAuth client_credentials flow.
 *
 * The shape of the POST body matches
 * ``bindu/auth/hydra/registration.py`` so the same Hydra can host
 * gateways and agents side-by-side without schema drift.
 */

import { sha256 } from "@noble/hashes/sha2.js"

export interface HydraClientCredentials {
  /** The DID, used as Hydra's client_id. */
  clientId: string
  /** Base64url-encoded 32-byte derivation — the OAuth2 client secret
   *  used in the client_credentials grant. */
  clientSecret: string
}

export interface EnsureHydraClientOpts {
  /** Hydra admin URL, e.g. http://hydra:4445 (no trailing slash). */
  adminUrl: string
  did: string
  clientName: string
  publicKeyBase58: string
  /** Deterministic secret derived from the seed — pass the value
   *  from ``deriveClientSecret``. */
  clientSecret: string
  /** OAuth scopes to request. Typical: ["openid", "offline",
   *  "agent:read", "agent:write"]. */
  scope: string[]
  /** Grant types. Typical for gateway: ["client_credentials"]. */
  grantTypes?: string[]
  /** Test hook. */
  fetch?: typeof fetch
}

/**
 * Deterministic client_secret derivation from the Ed25519 seed.
 *
 * Output: base64url-encoded 32 bytes. That's enough entropy to
 * satisfy Hydra's client_secret requirements (Hydra accepts any
 * non-empty string but ≥32 random bytes is the usual recommendation)
 * without introducing an extra secret the operator has to manage.
 *
 * The tag ensures the derivation is scoped — if a future piece of
 * Bindu also wants to derive a secret from the same seed for some
 * other purpose, it uses a different tag so the two secrets don't
 * collide.
 */
export function deriveClientSecret(seed: Uint8Array): string {
  const tag = new TextEncoder().encode("bindu-gateway-hydra-client-secret/v1")
  const combined = new Uint8Array(seed.length + tag.length)
  combined.set(seed, 0)
  combined.set(tag, seed.length)
  const digest = sha256(combined)
  return Buffer.from(digest)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "")
}

/**
 * Build the admin-API client payload. Shape matches what the Python
 * agent registration sends at
 * ``bindu/auth/hydra/registration.py:240-260``.
 */
function buildClientPayload(opts: EnsureHydraClientOpts): unknown {
  return {
    client_id: opts.did,
    client_secret: opts.clientSecret,
    client_name: opts.clientName,
    grant_types: opts.grantTypes ?? ["client_credentials"],
    response_types: ["code", "token"],
    scope: opts.scope.join(" "),
    token_endpoint_auth_method: "client_secret_post",
    metadata: {
      did: opts.did,
      public_key: opts.publicKeyBase58,
      key_type: "Ed25519",
      verification_method: "Ed25519VerificationKey2020",
      hybrid_auth: true,
      registered_at: new Date().toISOString(),
    },
  }
}

/**
 * Ensure a Hydra OAuth client exists for the given DID. Idempotent:
 *
 *   - If the client already exists (200 on GET), returns the
 *     credentials we passed in.
 *   - If not (404 on GET), POSTs the client payload and returns
 *     credentials.
 *   - Any other status (5xx, auth failure on admin API) is an error.
 *
 * Never persists the client_secret to disk — it's derived from the
 * seed, so operators only need to keep ``BINDU_GATEWAY_DID_SEED``
 * safe.
 */
export async function ensureHydraClient(
  opts: EnsureHydraClientOpts,
): Promise<HydraClientCredentials> {
  const fetcher = opts.fetch ?? fetch
  const base = opts.adminUrl.replace(/\/$/, "")
  const encoded = encodeURIComponent(opts.did)

  // Check if the client already exists.
  const getResp = await fetcher(`${base}/admin/clients/${encoded}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  })

  if (getResp.status === 200) {
    return { clientId: opts.did, clientSecret: opts.clientSecret }
  }
  if (getResp.status !== 404) {
    const body = await getResp.text().catch(() => "")
    throw new Error(
      `Hydra admin GET /admin/clients/${opts.did} returned ${getResp.status}: ${body.slice(0, 300)}`,
    )
  }

  // Not found — create it.
  const postResp = await fetcher(`${base}/admin/clients`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(buildClientPayload(opts)),
  })

  if (postResp.status !== 200 && postResp.status !== 201) {
    const body = await postResp.text().catch(() => "")
    throw new Error(
      `Hydra admin POST /admin/clients returned ${postResp.status}: ${body.slice(0, 300)}`,
    )
  }

  return { clientId: opts.did, clientSecret: opts.clientSecret }
}
