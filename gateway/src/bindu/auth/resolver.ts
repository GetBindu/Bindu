import { z } from "zod"
import type { LocalIdentity } from "../identity/local"
import type { TokenProvider } from "../identity/hydra-token"

/**
 * Per-peer auth configuration — describes how to authenticate against a
 * downstream Bindu agent.
 *
 * Supported variants:
 *
 *   * ``none`` — dev agents with auth disabled.
 *   * ``bearer`` — static JWT inline in the plan request.
 *   * ``bearer_env`` — read the token from a named process env var.
 *   * ``did_signed`` — OAuth bearer (from env) AND an Ed25519 signature
 *     of the request body produced by the gateway's DID identity. The
 *     body-aware signing means the headers MUST be built per-request,
 *     not once per peer, which is why ``buildAuthHeaders`` below is
 *     async and takes the serialized body as an argument.
 *
 * Phase 3 add: ``oauth2_client_credentials`` (full automatic token
 * refresh), ``mtls``.
 */

export const PeerAuth = z.discriminatedUnion("type", [
  z.object({ type: z.literal("none") }),
  z.object({ type: z.literal("bearer"), token: z.string() }),
  z.object({ type: z.literal("bearer_env"), envVar: z.string() }),
  z.object({
    type: z.literal("did_signed"),
    /** Optional. When set, the OAuth bearer token is read from this
     *  process env var. When omitted, the gateway's own Hydra token
     *  provider is used (auto-acquired via client_credentials at
     *  boot). ``tokenEnvVar`` is the escape hatch for federated
     *  deployments where the gateway needs different tokens per
     *  peer (e.g. each peer runs its own Hydra). The auto path is
     *  the common case: single shared Hydra, gateway registers
     *  once, every peer call uses the same cached token. */
    tokenEnvVar: z.string().optional(),
  }),
])
export type PeerAuth = z.infer<typeof PeerAuth>

/**
 * Build HTTP headers for a given auth descriptor. Async because the
 * ``did_signed`` variant signs the body with Ed25519.
 *
 * Arguments:
 *   - ``auth`` — the peer's auth descriptor (from the plan request's
 *     agent catalog)
 *   - ``body`` — the EXACT JSON-RPC body string that will be sent on
 *     the wire. The signature covers this exact byte sequence; any
 *     subsequent re-serialization breaks verification on the peer.
 *   - ``identity`` — the gateway's own DID identity. Required iff
 *     ``auth.type === "did_signed"``. For other types it's ignored.
 *
 * Never logs the resolved token or signature — callers printing
 * diagnostics should redact themselves.
 */
export async function buildAuthHeaders(
  auth: PeerAuth | undefined,
  body: string,
  identity?: LocalIdentity,
  tokenProvider?: TokenProvider,
): Promise<Record<string, string>> {
  if (!auth || auth.type === "none") return {}
  if (auth.type === "bearer") return { Authorization: `Bearer ${auth.token}` }
  if (auth.type === "bearer_env") {
    const v = process.env[auth.envVar]
    if (!v) {
      throw new Error(
        `auth: env var "${auth.envVar}" is not set (peer requires bearer auth from env)`,
      )
    }
    return { Authorization: `Bearer ${v}` }
  }
  if (auth.type === "did_signed") {
    if (!identity) {
      throw new Error(
        "auth: did_signed peer requires a gateway LocalIdentity — " +
          "check that BINDU_GATEWAY_DID_SEED is set at boot and that the " +
          "Client layer was built with makeLayer(identity).",
      )
    }

    // Token resolution:
    //   1. Peer-specific env var (escape hatch for federated deploys).
    //   2. Gateway-wide token provider (the auto path from
    //      BINDU_GATEWAY_HYDRA_TOKEN_URL at boot).
    //   3. Neither → clear error pointing at both options.
    let token: string
    if (auth.tokenEnvVar) {
      const v = process.env[auth.tokenEnvVar]
      if (!v) {
        throw new Error(
          `auth: env var "${auth.tokenEnvVar}" is not set ` +
            "(did_signed peer requires an OAuth bearer token alongside the DID signature)",
        )
      }
      token = v
    } else if (tokenProvider) {
      token = await tokenProvider.getToken()
    } else {
      throw new Error(
        "auth: did_signed peer has no tokenEnvVar set and the gateway " +
          "has no Hydra token provider configured. Set either " +
          "peer.auth.tokenEnvVar on the peer config, or " +
          "BINDU_GATEWAY_HYDRA_TOKEN_URL + BINDU_GATEWAY_HYDRA_SCOPE at " +
          "boot for the auto path.",
      )
    }

    const signed = await identity.sign(body)
    return {
      Authorization: `Bearer ${token}`,
      ...signed,
    }
  }
  // Exhaustiveness check — z.discriminatedUnion narrows auth.type above.
  const _exhaustive: never = auth
  return _exhaustive
}
