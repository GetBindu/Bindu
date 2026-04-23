/**
 * Gateway's own DID identity — used to sign outbound A2A requests so
 * DID-enforced Bindu peers accept them.
 *
 * Loads a 32-byte Ed25519 seed from the ``BINDU_GATEWAY_DID_SEED``
 * environment variable (base64 encoded). Derives the keypair. Exposes:
 *
 *   - ``did``              — the gateway's DID, format
 *                            ``did:bindu:{author}:{name}:{agentId}``
 *                            where ``agentId`` is derived deterministically
 *                            from the public key so the DID is stable
 *                            across restarts as long as the seed doesn't
 *                            change.
 *   - ``publicKeyBase58``  — for publishing in /.well-known/did.json and
 *                            for registering with Hydra's client metadata.
 *   - ``sign(body)``       — produces the three X-DID-* headers for a
 *                            given exact body string. Matches the Python
 *                            verifier's byte-exact expectation — see
 *                            ``bindu/utils/did/signature.py``:
 *
 *                              payload_str = json.dumps(
 *                                  {"body": body, "did": did, "timestamp": ts},
 *                                  sort_keys=True,
 *                              )
 *                              # Python's default separators have spaces
 *                              # after `:` and `,` — we match that here.
 *
 * The signer refuses to operate if the env var is missing. That's
 * intentional: a gateway configured for DID-signed peers that silently
 * starts without a signing key produces mysterious 403s downstream.
 * Fail fast at boot.
 */

import "./bootstrap" // MUST be first — wires ed25519.etc.sha512Sync
import * as ed25519 from "@noble/ed25519"
import { sha256 } from "@noble/hashes/sha2.js"
import bs58 from "bs58"

/** Headers the signer produces, matching the Python middleware's contract. */
export interface DidSignatureHeaders {
  "X-DID": string
  "X-DID-Timestamp": string
  "X-DID-Signature": string
}

export interface LocalIdentity {
  readonly did: string
  readonly publicKeyBase58: string
  /** Sign the given EXACT body string. Callers MUST serialize their
   *  request body once and pass those exact bytes both here and to the
   *  HTTP transport. Any mismatch → crypto_mismatch at the verifier. */
  sign(body: string, timestamp?: number): Promise<DidSignatureHeaders>
}

export interface LocalIdentityConfig {
  /** Author identifier (typically an email). Embedded in the DID so
   *  operators can tell which gateway instance signed a request when
   *  reading logs. */
  author: string
  /** Short gateway name. Embedded in the DID. */
  name: string
  /** Optional override for the env var name. Defaults to
   *  ``BINDU_GATEWAY_DID_SEED``. Override is used only by tests. */
  seedEnvVar?: string
}

const DEFAULT_SEED_ENV = "BINDU_GATEWAY_DID_SEED"

/**
 * Sanitize an author identifier into DID-safe form. Mirrors
 * ``bindu/extensions/did/did_agent_extension.py``'s convention:
 * email-like strings get ``@`` → ``_at_`` and ``.`` → ``_`` so the
 * result contains no colons (which would break the 5-part format).
 */
export function sanitizeAuthor(raw: string): string {
  return raw.replace(/@/g, "_at_").replace(/\./g, "_")
}

/**
 * Derive a stable 16-byte agent id from the public key. Formatted as a
 * UUID so it matches the Python ``did_agent_extension`` format. Two
 * gateway instances sharing the same seed will produce the same DID —
 * which is correct for horizontal scaling behind a load balancer.
 */
export function deriveAgentId(publicKey: Uint8Array): string {
  const hash = sha256(publicKey)
  const h = Array.from(hash.slice(0, 16))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20, 32)}`
}

/** Decode a base64-encoded 32-byte seed. */
function decodeSeed(b64: string): Uint8Array {
  // Handle both standard and URL-safe base64 just in case.
  const normalized = b64.replace(/-/g, "+").replace(/_/g, "/")
  const buf = Buffer.from(normalized, "base64")
  if (buf.length !== 32) {
    throw new Error(
      `BINDU_GATEWAY_DID_SEED must decode to exactly 32 bytes (got ${buf.length}). ` +
        `Generate one with: python -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\"`,
    )
  }
  return new Uint8Array(buf)
}

/**
 * Match Python's ``json.dumps(obj, sort_keys=True)`` output byte-for-byte.
 *
 * Python's default separators are ``(", ", ": ")`` — WITH spaces after
 * ``:`` and ``,``. ``JSON.stringify`` uses ``(",", ":")`` — no spaces.
 * The one-character difference produces a different signing input, so
 * the verifier reconstructs a different payload and returns
 * ``crypto_mismatch`` even when the caller signed exactly the "right"
 * data. This helper replicates Python's spacing exactly.
 *
 * Also sorts object keys alphabetically at every nesting level — again
 * matching Python's ``sort_keys=True``.
 */
export function pythonSortedJson(value: unknown): string {
  if (value === null) return "null"
  if (typeof value === "boolean") return value ? "true" : "false"
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error(`Non-finite number not JSON-serializable: ${value}`)
    }
    return String(value)
  }
  if (typeof value === "string") return JSON.stringify(value)
  if (Array.isArray(value)) {
    return "[" + value.map(pythonSortedJson).join(", ") + "]"
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>
    const keys = Object.keys(obj).sort()
    return (
      "{" +
      keys
        .map((k) => JSON.stringify(k) + ": " + pythonSortedJson(obj[k]))
        .join(", ") +
      "}"
    )
  }
  throw new Error(`Unsupported type for Python-compat JSON: ${typeof value}`)
}

/**
 * Low-level signer. Reproduces the Python
 * ``sign_request`` + ``create_signature_payload`` pipeline byte-for-byte:
 *
 *   1. Build ``{"body": body, "did": did, "timestamp": ts}``
 *   2. Serialize with Python-compatible ``json.dumps(sort_keys=True)``
 *   3. Ed25519-sign the UTF-8 bytes of the serialized string
 *   4. Base58-encode the signature
 *
 * Split out from ``loadLocalIdentity`` so the cross-language contract
 * test can drive it with canonical fixture inputs (a fixed seed,
 * fixed DID, fixed body, fixed timestamp) and assert byte-exact
 * agreement with the Python signer.
 */
export async function signPayload(params: {
  seed: Uint8Array
  did: string
  body: string
  timestamp: number
}): Promise<DidSignatureHeaders> {
  const payloadStr = pythonSortedJson({
    body: params.body,
    did: params.did,
    timestamp: params.timestamp,
  })
  const sig = await ed25519.signAsync(
    new TextEncoder().encode(payloadStr),
    params.seed,
  )
  return {
    "X-DID": params.did,
    "X-DID-Timestamp": String(params.timestamp),
    "X-DID-Signature": bs58.encode(sig),
  }
}

/**
 * Load and construct the gateway's DID identity. Throws if the seed
 * env var is missing or malformed.
 */
export function loadLocalIdentity(config: LocalIdentityConfig): LocalIdentity {
  const envName = config.seedEnvVar ?? DEFAULT_SEED_ENV
  const seedB64 = process.env[envName]
  if (!seedB64) {
    throw new Error(
      `${envName} is not set. The gateway needs a 32-byte Ed25519 seed ` +
        `(base64) to sign outbound DID requests. Generate one with:\n` +
        `  python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"\n` +
        `and set ${envName} before starting the gateway.`,
    )
  }

  const seed = decodeSeed(seedB64)
  const publicKey = ed25519.getPublicKey(seed)
  const publicKeyBase58 = bs58.encode(publicKey)
  const agentId = deriveAgentId(publicKey)
  const did = `did:bindu:${sanitizeAuthor(config.author)}:${config.name}:${agentId}`

  return {
    did,
    publicKeyBase58,
    sign: (body, timestamp) =>
      signPayload({
        seed,
        did,
        body,
        timestamp: timestamp ?? Math.floor(Date.now() / 1000),
      }),
  }
}
