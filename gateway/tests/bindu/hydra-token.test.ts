/**
 * Tests for the OAuth client_credentials token provider.
 *
 * The critical properties:
 *
 *   1. Caches across calls — successive getToken() returns the
 *      same string without re-fetching while the cached token has
 *      headroom.
 *   2. Refreshes proactively — when remaining lifetime drops below
 *      refreshThresholdSec, the next getToken() fetches a fresh
 *      token. Verified with a controlled clock.
 *   3. Coalesces concurrent callers — N concurrent getToken() calls
 *      during a refresh share a single in-flight fetch. Prevents
 *      stampede + rate-limit risk during a plan's tool-call
 *      fan-out.
 *   4. Surfaces Hydra errors with status + body — so operators can
 *      diagnose auth / scope / network issues.
 */

import { describe, it, expect, vi } from "vitest"
import { createTokenProvider } from "../../src/bindu/identity/hydra-token"

function tokenResponse(access_token: string, expires_in = 3600): Response {
  return new Response(
    JSON.stringify({ access_token, expires_in, token_type: "bearer" }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    },
  )
}

const OPTS = {
  tokenUrl: "http://hydra:4444/oauth2/token",
  clientId: "did:bindu:test",
  clientSecret: "secret",
  scope: ["openid", "agent:execute"],
}

describe("createTokenProvider", () => {
  it("fetches on first call, caches for subsequent calls", async () => {
    const fetchMock = vi.fn(async () => tokenResponse("abc", 3600))
    const provider = createTokenProvider({
      ...OPTS,
      fetch: fetchMock as any,
    })

    expect(await provider.getToken()).toBe("abc")
    expect(await provider.getToken()).toBe("abc")
    expect(await provider.getToken()).toBe("abc")
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("sends the right form body to Hydra", async () => {
    const sent: { body: string }[] = []
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      sent.push({ body: init.body as string })
      return tokenResponse("x")
    })

    await createTokenProvider({
      ...OPTS,
      fetch: fetchMock as any,
    }).getToken()

    const params = new URLSearchParams(sent[0].body)
    expect(params.get("grant_type")).toBe("client_credentials")
    expect(params.get("client_id")).toBe(OPTS.clientId)
    expect(params.get("client_secret")).toBe(OPTS.clientSecret)
    expect(params.get("scope")).toBe("openid agent:execute")
  })

  it("refreshes when cache has less than refreshThresholdSec remaining", async () => {
    let nowMs = 1_000_000
    let serial = 0
    const fetchMock = vi.fn(async () => {
      serial += 1
      return tokenResponse(`tok-${serial}`, 60) // 60s lifetime
    })

    const provider = createTokenProvider({
      ...OPTS,
      refreshThresholdSec: 30,
      fetch: fetchMock as any,
      now: () => nowMs,
    })

    // First call fetches tok-1.
    expect(await provider.getToken()).toBe("tok-1")
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // Advance 10s — still plenty of runway. Cached.
    nowMs += 10_000
    expect(await provider.getToken()).toBe("tok-1")
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // Advance past the refresh threshold (60s - 30s = 30s into life).
    nowMs += 25_000
    expect(await provider.getToken()).toBe("tok-2")
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it("coalesces concurrent callers into one in-flight fetch", async () => {
    let resolve: (v: Response) => void = () => {}
    const pending = new Promise<Response>((r) => {
      resolve = r
    })

    const fetchMock = vi.fn(async () => pending)

    const provider = createTokenProvider({
      ...OPTS,
      fetch: fetchMock as any,
    })

    // Fire three concurrent callers before the fetch resolves.
    const [a, b, c] = [
      provider.getToken(),
      provider.getToken(),
      provider.getToken(),
    ]

    // Exactly one fetch in flight.
    expect(fetchMock).toHaveBeenCalledTimes(1)

    resolve(tokenResponse("shared-tok"))

    const [ra, rb, rc] = await Promise.all([a, b, c])
    expect(ra).toBe("shared-tok")
    expect(rb).toBe("shared-tok")
    expect(rc).toBe("shared-tok")
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("surfaces Hydra error with status and body", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response("invalid_client", {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
    )

    const provider = createTokenProvider({
      ...OPTS,
      fetch: fetchMock as any,
    })

    await expect(provider.getToken()).rejects.toThrow(/401.*invalid_client/)
  })

  it("rejects malformed token responses", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify({ something: "else" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    )

    const provider = createTokenProvider({
      ...OPTS,
      fetch: fetchMock as any,
    })

    await expect(provider.getToken()).rejects.toThrow(/access_token/)
  })

  it("re-fetches after an in-flight failure (not stuck in bad state)", async () => {
    let serial = 0
    const fetchMock = vi.fn(async () => {
      serial += 1
      if (serial === 1) return new Response("boom", { status: 500 })
      return tokenResponse("recovered")
    })

    const provider = createTokenProvider({
      ...OPTS,
      fetch: fetchMock as any,
    })

    await expect(provider.getToken()).rejects.toThrow()
    expect(await provider.getToken()).toBe("recovered")
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})
