/**
 * Tests for GET /.well-known/did.json — the gateway's self-published
 * DID document.
 *
 * Contract the peers depend on:
 *
 *   1. Document has a valid W3C DID Core shape (``@context``, ``id``,
 *      ``authentication``) with Bindu's extension namespace.
 *   2. ``id`` exactly matches the gateway's loaded DID — peers compare
 *      this against the DID they resolved.
 *   3. ``publicKeyBase58`` exactly matches what outbound DID-signed
 *      requests would be signed against. If these drift, verification
 *      fails on the peer side with ``crypto_mismatch``.
 *   4. Content-Type is ``application/did+json`` per W3C DID Core —
 *      plain ``application/json`` is tolerated by most resolvers but
 *      stricter ones reject it.
 *   5. ``created`` is deliberately absent — see api/did-route.ts for
 *      the rationale. This test guards the decision so it's not
 *      re-introduced accidentally.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest"
import { Hono } from "hono"
import {
  buildDidDocument,
  buildDidHandler,
} from "../../src/api/did-route"
import { loadLocalIdentity } from "../../src/bindu/identity/local"

const TEST_ENV = "TEST_DID_ROUTE_SEED"

function setSeedEnv(b64: string | undefined) {
  if (b64 === undefined) delete process.env[TEST_ENV]
  else process.env[TEST_ENV] = b64
}

function makeIdentity() {
  // 32 zero bytes — deterministic test seed. Matches the cross-language
  // fixture in identity-local.test.ts so a failure here and a failure
  // there point at the same drift.
  setSeedEnv(Buffer.from(new Uint8Array(32)).toString("base64"))
  return loadLocalIdentity({
    author: "ops@example.com",
    name: "gateway",
    seedEnvVar: TEST_ENV,
  })
}

// ---------------------------------------------------------------------------
// buildDidDocument — pure shape
// ---------------------------------------------------------------------------

describe("buildDidDocument", () => {
  afterEach(() => setSeedEnv(undefined))

  it("has the W3C DID Core + Bindu @context", () => {
    const doc = buildDidDocument(makeIdentity())
    expect(doc["@context"]).toEqual([
      "https://www.w3.org/ns/did/v1",
      "https://getbindu.com/ns/v1",
    ])
  })

  it("id equals the identity DID exactly", () => {
    const id = makeIdentity()
    const doc = buildDidDocument(id)
    expect(doc.id).toBe(id.did)
  })

  it("authentication has exactly one Ed25519VerificationKey2020 entry", () => {
    const doc = buildDidDocument(makeIdentity())
    expect(doc.authentication).toHaveLength(1)
    const method = doc.authentication[0]
    expect(method.type).toBe("Ed25519VerificationKey2020")
  })

  it("verification method id is `${did}#key-1`", () => {
    const id = makeIdentity()
    const doc = buildDidDocument(id)
    expect(doc.authentication[0].id).toBe(`${id.did}#key-1`)
  })

  it("verification method controller is the DID itself (self-controlled)", () => {
    const id = makeIdentity()
    const doc = buildDidDocument(id)
    expect(doc.authentication[0].controller).toBe(id.did)
  })

  it("publicKeyBase58 equals identity.publicKeyBase58 byte-exact", () => {
    const id = makeIdentity()
    const doc = buildDidDocument(id)
    expect(doc.authentication[0].publicKeyBase58).toBe(id.publicKeyBase58)
  })

  it("does not emit ``created`` (stateless gateway, no persisted birth time)", () => {
    const doc = buildDidDocument(makeIdentity()) as unknown as Record<string, unknown>
    expect(doc.created).toBeUndefined()
  })

  it("is deterministic — same identity produces identical documents", () => {
    const id = makeIdentity()
    expect(buildDidDocument(id)).toEqual(buildDidDocument(id))
  })
})

// ---------------------------------------------------------------------------
// buildDidHandler — HTTP behavior
// ---------------------------------------------------------------------------

describe("buildDidHandler — HTTP response shape", () => {
  afterEach(() => setSeedEnv(undefined))

  function mountApp() {
    const id = makeIdentity()
    const app = new Hono()
    app.get("/.well-known/did.json", buildDidHandler(id))
    return { app, identity: id }
  }

  it("200 on the well-known path", async () => {
    const { app } = mountApp()
    const res = await app.request("/.well-known/did.json")
    expect(res.status).toBe(200)
  })

  it("Content-Type is application/did+json", async () => {
    const { app } = mountApp()
    const res = await app.request("/.well-known/did.json")
    expect(res.headers.get("content-type")).toContain("application/did+json")
  })

  it("Cache-Control is set (5-minute public cache)", async () => {
    const { app } = mountApp()
    const res = await app.request("/.well-known/did.json")
    const cc = res.headers.get("cache-control") ?? ""
    expect(cc).toContain("public")
    expect(cc).toContain("max-age=300")
  })

  it("response body parses as JSON and matches buildDidDocument output", async () => {
    const { app, identity } = mountApp()
    const res = await app.request("/.well-known/did.json")
    const body = await res.json()
    expect(body).toEqual(buildDidDocument(identity))
  })

  it("repeated requests return byte-identical bodies (safe to hash/cache)", async () => {
    const { app } = mountApp()
    const a = await (await app.request("/.well-known/did.json")).text()
    const b = await (await app.request("/.well-known/did.json")).text()
    expect(a).toBe(b)
  })
})

// ---------------------------------------------------------------------------
// Peer-resolution contract — what an A2A peer will actually do with this
// ---------------------------------------------------------------------------

describe("peer-resolution contract", () => {
  afterEach(() => setSeedEnv(undefined))

  it("a peer can round-trip: fetch doc → extract pubkey → matches identity's key", async () => {
    const id = makeIdentity()
    const app = new Hono()
    app.get("/.well-known/did.json", buildDidHandler(id))

    // Simulates what a DID-enforced peer does when it needs to verify
    // a signature from this gateway: resolve the DID, pull the key,
    // and use it. The key is what signatures get verified against —
    // this is the invariant that must not drift.
    const res = await app.request("/.well-known/did.json")
    const doc = (await res.json()) as {
      authentication: Array<{ publicKeyBase58: string }>
    }
    const pubkeyFromDoc = doc.authentication[0].publicKeyBase58

    expect(pubkeyFromDoc).toBe(id.publicKeyBase58)
  })
})
