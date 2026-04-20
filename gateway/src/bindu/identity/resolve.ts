import { DIDDocument } from "../protocol/agent-card"
import type { z } from "zod"

/**
 * Fetch + cache a peer's DID Document.
 *
 * Bindu agents expose `POST /did/resolve` with body `{ did }`. The
 * response is a W3C DID Document. We cache by DID string with a short TTL
 * (default 5 min) since rotation is infrequent but not nonexistent.
 */

export type DIDDoc = z.infer<typeof DIDDocument>

interface CacheEntry {
  doc: DIDDoc
  fetchedAt: number
}

export interface Resolver {
  resolve(peerUrl: string, did: string, opts?: { forceRefresh?: boolean }): Promise<DIDDoc>
  invalidate(did: string): void
  clear(): void
}

export interface CreateOptions {
  ttlMs?: number
  fetch?: typeof fetch
}

export function createResolver(options: CreateOptions = {}): Resolver {
  const ttl = options.ttlMs ?? 5 * 60 * 1000
  const fetcher = options.fetch ?? fetch
  const cache = new Map<string, CacheEntry>()

  async function resolve(peerUrl: string, did: string, opts?: { forceRefresh?: boolean }): Promise<DIDDoc> {
    const existing = cache.get(did)
    if (!opts?.forceRefresh && existing && Date.now() - existing.fetchedAt < ttl) {
      return existing.doc
    }

    const resp = await fetcher(`${stripTrailingSlash(peerUrl)}/did/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ did }),
    })
    if (!resp.ok) {
      throw new Error(`did/resolve HTTP ${resp.status} for ${did}`)
    }
    const raw = await resp.json()
    const doc = DIDDocument.parse(raw)
    cache.set(did, { doc, fetchedAt: Date.now() })
    return doc
  }

  return {
    resolve,
    invalidate: (did) => void cache.delete(did),
    clear: () => cache.clear(),
  }
}

function stripTrailingSlash(u: string): string {
  return u.endsWith("/") ? u.slice(0, -1) : u
}

/** Extract the primary public key (base58) from a DID Document. */
export function primaryPublicKeyBase58(doc: DIDDoc): string | null {
  const auth = doc.authentication ?? []
  for (const entry of auth) {
    if (typeof entry === "object" && entry && "publicKeyBase58" in entry) {
      const pk = (entry as { publicKeyBase58?: string }).publicKeyBase58
      if (pk) return pk
    }
  }
  const verMethod = doc.verificationMethod ?? []
  for (const m of verMethod) {
    if (m.publicKeyBase58) return m.publicKeyBase58
  }
  return null
}
