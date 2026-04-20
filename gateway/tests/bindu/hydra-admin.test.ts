/**
 * Tests for the Hydra admin client — idempotent OAuth client
 * registration for the gateway's own DID.
 *
 * Coverage priorities:
 *   1. ``deriveClientSecret`` is deterministic and scoped (same seed
 *      always produces the same secret; different tags would produce
 *      different secrets).
 *   2. ``ensureHydraClient`` is idempotent: an existing client (200
 *      GET) means no POST. A missing client (404 GET) means POST.
 *   3. Any non-200/404 from the GET, or non-2xx from the POST, is an
 *      error with the Hydra response body surfaced so operators can
 *      diagnose auth / network / permission issues.
 */

import { describe, it, expect, vi } from "vitest"
import {
  deriveClientSecret,
  ensureHydraClient,
} from "../../src/bindu/identity/hydra-admin"

function mockResponse(body: unknown, status = 200): Response {
  return new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

const FIXTURE = {
  adminUrl: "http://hydra:4445",
  did: "did:bindu:test:gateway:abc",
  clientName: "gateway",
  publicKeyBase58: "4zvwRjXUKGfvwnParsHAS3HuSVzV5cA4McphgmoCtajS",
  scope: ["openid", "agent:execute"],
}

describe("deriveClientSecret", () => {
  it("is deterministic — same seed → same secret", () => {
    const seed = new Uint8Array(32).fill(1)
    expect(deriveClientSecret(seed)).toBe(deriveClientSecret(seed))
  })

  it("different seeds → different secrets", () => {
    expect(deriveClientSecret(new Uint8Array(32).fill(1))).not.toBe(
      deriveClientSecret(new Uint8Array(32).fill(2)),
    )
  })

  it("produces base64url output (no +/= padding)", () => {
    const secret = deriveClientSecret(new Uint8Array(32).fill(0))
    expect(secret).toMatch(/^[A-Za-z0-9_-]+$/)
    expect(secret.length).toBeGreaterThanOrEqual(32)
  })
})

describe("ensureHydraClient — idempotent registration", () => {
  it("GET 200 means client exists — no POST", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith(`/admin/clients/${encodeURIComponent(FIXTURE.did)}`)) {
        return mockResponse({ client_id: FIXTURE.did }, 200)
      }
      throw new Error(`unexpected url: ${url}`)
    })

    const creds = await ensureHydraClient({
      ...FIXTURE,
      clientSecret: "secret-x",
      fetch: fetchMock as any,
    })

    expect(creds).toEqual({ clientId: FIXTURE.did, clientSecret: "secret-x" })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("GET 404 then POST 201 — creates the client with the right payload", async () => {
    const sentBodies: string[] = []
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (init?.method === "GET" || !init?.method) {
        return mockResponse("", 404)
      }
      sentBodies.push(init.body as string)
      return mockResponse({ client_id: FIXTURE.did }, 201)
    })

    const creds = await ensureHydraClient({
      ...FIXTURE,
      clientSecret: "secret-abc",
      fetch: fetchMock as any,
    })

    expect(creds).toEqual({
      clientId: FIXTURE.did,
      clientSecret: "secret-abc",
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)

    // POST body carries the expected Hydra client shape.
    const posted = JSON.parse(sentBodies[0])
    expect(posted.client_id).toBe(FIXTURE.did)
    expect(posted.client_secret).toBe("secret-abc")
    expect(posted.client_name).toBe(FIXTURE.clientName)
    expect(posted.grant_types).toEqual(["client_credentials"])
    expect(posted.token_endpoint_auth_method).toBe("client_secret_post")
    expect(posted.scope).toBe("openid agent:execute")
    expect(posted.metadata.did).toBe(FIXTURE.did)
    expect(posted.metadata.public_key).toBe(FIXTURE.publicKeyBase58)
    expect(posted.metadata.key_type).toBe("Ed25519")
    expect(posted.metadata.hybrid_auth).toBe(true)
  })

  it("GET 5xx on admin URL surfaces the status and body", async () => {
    const fetchMock = vi.fn(async () => mockResponse("hydra down", 503))
    await expect(
      ensureHydraClient({
        ...FIXTURE,
        clientSecret: "s",
        fetch: fetchMock as any,
      }),
    ).rejects.toThrow(/503.*hydra down/)
  })

  it("POST 4xx after 404 GET surfaces the error", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      if (!init?.method || init.method === "GET")
        return mockResponse("", 404)
      return mockResponse("forbidden", 403)
    })

    await expect(
      ensureHydraClient({
        ...FIXTURE,
        clientSecret: "s",
        fetch: fetchMock as any,
      }),
    ).rejects.toThrow(/403.*forbidden/)
  })

  it("accepts grantTypes override (e.g. adding authorization_code)", async () => {
    const sentBodies: string[] = []
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      if (!init?.method || init.method === "GET")
        return mockResponse("", 404)
      sentBodies.push(init.body as string)
      return mockResponse("", 201)
    })

    await ensureHydraClient({
      ...FIXTURE,
      clientSecret: "s",
      grantTypes: ["client_credentials", "refresh_token"],
      fetch: fetchMock as any,
    })

    const posted = JSON.parse(sentBodies[0])
    expect(posted.grant_types).toEqual([
      "client_credentials",
      "refresh_token",
    ])
  })

  it("trailing slash on adminUrl is tolerated", async () => {
    let getUrl = ""
    const fetchMock = vi.fn(async (url: string) => {
      getUrl = url
      return mockResponse("", 200)
    })

    await ensureHydraClient({
      ...FIXTURE,
      adminUrl: "http://hydra:4445/",
      clientSecret: "s",
      fetch: fetchMock as any,
    })

    // No double slash in the constructed URL.
    expect(getUrl).not.toContain("//admin")
    expect(getUrl).toContain("/admin/clients/")
  })
})
