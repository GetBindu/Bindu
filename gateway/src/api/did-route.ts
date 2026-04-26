import type { Context as HonoContext } from "hono"
import type { LocalIdentity } from "../bindu/identity/local"

/**
 * GET /.well-known/did.json — the gateway's self-published DID document.
 *
 * Lets any A2A peer resolve the gateway's DID to the Ed25519 public key
 * without round-tripping through Hydra admin. Matches the shape W3C DID
 * Core + the Bindu agent extension publish:
 *
 *   {
 *     "@context":       [w3c, getbindu],
 *     "id":             "did:bindu:...",
 *     "authentication": [{ id, type, controller, publicKeyBase58 }]
 *   }
 *
 * Deliberately omits ``created``. The gateway's identity is env-driven
 * and stateless — there's no persisted "first published" moment to
 * report. Emitting the process start time or current-now would mislead
 * clients into thinking the key was rotated at that moment. W3C DID
 * Core v1 has ``created`` as optional; absence is valid.
 *
 * Deliberately unauthenticated. Well-known endpoints are public by
 * spec — the whole point is that anyone can resolve the DID without
 * credentials.
 */

const CONTEXT = [
  "https://www.w3.org/ns/did/v1",
  "https://getbindu.com/ns/v1",
] as const

/** Verification method shape — one entry per usable public key. */
export interface GatewayVerificationMethod {
  readonly id: string
  readonly type: "Ed25519VerificationKey2020"
  readonly controller: string
  readonly publicKeyBase58: string
}

/** The gateway's DID document. See module docstring for why ``created`` is absent. */
export interface GatewayDidDocument {
  readonly "@context": readonly string[]
  readonly id: string
  readonly authentication: readonly GatewayVerificationMethod[]
}

/**
 * Build the DID document from an identity. Pure — safe to call once at
 * boot and cache the result for the life of the process.
 */
export function buildDidDocument(identity: LocalIdentity): GatewayDidDocument {
  return {
    "@context": CONTEXT,
    id: identity.did,
    authentication: [
      {
        id: `${identity.did}#key-1`,
        type: "Ed25519VerificationKey2020",
        controller: identity.did,
        publicKeyBase58: identity.publicKeyBase58,
      },
    ],
  }
}

/**
 * Build the Hono handler. Serializes the document once, returns the
 * same bytes on every request — the content doesn't change for the
 * lifetime of the process, so caching the serialization saves a tiny
 * amount of per-request work and (more importantly) guarantees
 * byte-stability if a client hashes the response.
 *
 * Content-Type is ``application/did+json`` per W3C DID Core — not
 * plain ``application/json``. Some DID resolvers check the media type.
 */
export function buildDidHandler(identity: LocalIdentity) {
  const document = buildDidDocument(identity)
  const body = JSON.stringify(document)
  return (c: HonoContext) =>
    c.body(body, 200, {
      "Content-Type": "application/did+json",
      // 5-minute cache. The key doesn't rotate without a gateway
      // restart, so short TTL is just defensive against bad caches
      // holding forever. Peers that need certainty still hit us fresh.
      "Cache-Control": "public, max-age=300",
    })
}
