import "./bootstrap"
import * as ed25519 from "@noble/ed25519"
import bs58 from "bs58"

/**
 * Verify an Ed25519 signature over the raw UTF-8 bytes of a text payload.
 *
 * Phase 0 confirmed: Bindu signs `part.text.encode("utf-8")` — no canonical
 * JSON, no JWS envelope. Signature bytes are base58-encoded and live in
 * `part.metadata["did.message.signature"]`.
 *
 * @returns true if the signature is valid, false otherwise. Never throws
 * for invalid input — malformed signatures / pubkeys return false so
 * callers can attribute via peer trust scoring without separate error paths.
 */
export async function verify(
  text: string,
  signatureBase58: string,
  publicKeyBase58: string,
): Promise<boolean> {
  try {
    const sig = bs58.decode(signatureBase58)
    const pub = bs58.decode(publicKeyBase58)
    if (pub.length !== 32) return false
    if (sig.length !== 64) return false
    const message = new TextEncoder().encode(text)
    return await ed25519.verifyAsync(sig, message, pub)
  } catch {
    return false
  }
}

/**
 * Synchronous variant of `verify`. Uses the sync sha512 hook configured in
 * bootstrap.ts. Prefer async when you're already inside an async context —
 * the bindu client's fetch chain is all async anyway.
 */
export function verifySync(
  text: string,
  signatureBase58: string,
  publicKeyBase58: string,
): boolean {
  try {
    const sig = bs58.decode(signatureBase58)
    const pub = bs58.decode(publicKeyBase58)
    if (pub.length !== 32) return false
    if (sig.length !== 64) return false
    const message = new TextEncoder().encode(text)
    return ed25519.verify(sig, message, pub)
  } catch {
    return false
  }
}

/**
 * Walk an Artifact's text parts and verify each signature present.
 * Returns a summary — callers decide what to do with partial failures.
 */
export interface VerifyArtifactInput {
  parts: Array<{
    kind: string
    text?: string
    metadata?: Record<string, unknown> | undefined
  }>
  publicKeyBase58: string
}

export interface VerifyArtifactOutcome {
  /** true if every signed text part verified; false if any verification failed. */
  ok: boolean
  /** count of text parts carrying a signature. */
  signed: number
  /** count of text parts whose signature verified. */
  verified: number
  /** count of text parts without a signature. */
  unsigned: number
}

export async function verifyArtifact(input: VerifyArtifactInput): Promise<VerifyArtifactOutcome> {
  let signed = 0
  let verified = 0
  let unsigned = 0

  for (const p of input.parts) {
    if (p.kind !== "text" || !p.text) continue
    const sig = (p.metadata as Record<string, unknown> | undefined)?.["did.message.signature"]
    if (typeof sig !== "string") {
      unsigned += 1
      continue
    }
    signed += 1
    if (await verify(p.text, sig, input.publicKeyBase58)) verified += 1
  }

  return {
    ok: signed === 0 ? true : signed === verified,
    signed,
    verified,
    unsigned,
  }
}
