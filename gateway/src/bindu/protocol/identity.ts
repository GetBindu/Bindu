import type { AgentCard } from "./agent-card"

/**
 * DID helpers.
 *
 * Phase 0 found that `AgentCard.id` can be a bare UUID (not a DID). The
 * real DID lives in `capabilities.extensions[].uri` with a `did:bindu:` or
 * `did:key:` prefix. `getPeerDID(card)` checks both locations.
 */

const DID_PREFIX = /^did:[a-zA-Z0-9]+:/

export function getPeerDID(card: AgentCard | null | undefined): string | null {
  if (!card) return null

  if (typeof card.id === "string" && DID_PREFIX.test(card.id)) {
    return card.id
  }

  const extensions = card.capabilities?.extensions ?? []
  for (const ext of extensions) {
    if (typeof ext.uri === "string" && DID_PREFIX.test(ext.uri)) {
      return ext.uri
    }
  }

  return null
}

/**
 * Parse a `did:bindu:<email>:<agent_name>:<hash>` or `did:key:<multibase>`
 * into its segments. Returns null for anything else.
 *
 * The `hash` segment is the first 32 hex chars of `sha256(publicKey)`, but
 * deployed agents emit it as a UUID (`438b4815-7ebe-d853-b95d-48b32b68fa3a`).
 * We accept both; callers can strip dashes when they need the canonical
 * form for hash comparison.
 */
export interface BinduDID {
  method: "bindu"
  author: string
  agentName: string
  agentId: string
  raw: string
}

export interface KeyDID {
  method: "key"
  publicKeyMultibase: string
  raw: string
}

export type ParsedDID = BinduDID | KeyDID

export function parseDID(did: string): ParsedDID | null {
  if (did.startsWith("did:bindu:")) {
    const rest = did.slice("did:bindu:".length)
    const segments = rest.split(":")
    if (segments.length < 3) return null
    // Bindu format: <author>:<agent_name>:<agent_id>
    // agent_name may contain underscores but not colons; agent_id is last.
    const [author, agentName, agentId] = [segments[0], segments[1], segments.slice(2).join(":")]
    return { method: "bindu", author, agentName, agentId, raw: did }
  }
  if (did.startsWith("did:key:")) {
    return {
      method: "key",
      publicKeyMultibase: did.slice("did:key:".length),
      raw: did,
    }
  }
  return null
}

/**
 * Extract the hex form of a did:bindu agent_id (strip UUID dashes).
 * Returns null if the DID isn't did:bindu or the id doesn't look hex-ish.
 */
export function agentIdHex(did: string): string | null {
  const parsed = parseDID(did)
  if (!parsed || parsed.method !== "bindu") return null
  const hex = parsed.agentId.replace(/-/g, "")
  if (!/^[0-9a-f]{32}$/i.test(hex)) return null
  return hex.toLowerCase()
}
