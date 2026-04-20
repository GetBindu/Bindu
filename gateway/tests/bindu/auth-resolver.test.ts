/**
 * Tests for auth/resolver — the peer auth descriptor and the async
 * ``buildAuthHeaders`` that turns it into HTTP headers.
 *
 * The ``did_signed`` path is the load-bearing new case. Its failures
 * (missing identity, missing OAuth env var) must produce clear,
 * actionable errors, because a misconfigured gateway signing attempt
 * would otherwise manifest as a 403 with a ``crypto_mismatch`` reason
 * three layers downstream.
 */

import { describe, it, expect, afterEach } from "vitest"
import { buildAuthHeaders, PeerAuth } from "../../src/bindu/auth/resolver"
import { loadLocalIdentity } from "../../src/bindu/identity/local"

const SEED_ENV = "TEST_AUTH_RESOLVER_SEED"
const TOKEN_ENV = "TEST_AUTH_RESOLVER_TOKEN"

function withEnv(vars: Record<string, string | undefined>): void {
  for (const [k, v] of Object.entries(vars)) {
    if (v === undefined) delete process.env[k]
    else process.env[k] = v
  }
}

describe("PeerAuth schema", () => {
  it("accepts all four variants", () => {
    expect(PeerAuth.safeParse({ type: "none" }).success).toBe(true)
    expect(PeerAuth.safeParse({ type: "bearer", token: "x" }).success).toBe(true)
    expect(PeerAuth.safeParse({ type: "bearer_env", envVar: "X" }).success).toBe(true)
    expect(
      PeerAuth.safeParse({ type: "did_signed", tokenEnvVar: "X" }).success,
    ).toBe(true)
  })

  it("rejects unknown variants and missing required fields", () => {
    expect(PeerAuth.safeParse({ type: "unknown" } as any).success).toBe(false)
    expect(PeerAuth.safeParse({ type: "bearer" } as any).success).toBe(false)
    // did_signed: tokenEnvVar is optional (falls back to gateway
    // token provider), so `{ type: "did_signed" }` alone is valid.
    expect(PeerAuth.safeParse({ type: "did_signed" }).success).toBe(true)
    expect(
      PeerAuth.safeParse({ type: "did_signed", tokenEnvVar: 42 } as any).success,
    ).toBe(false)
  })
})

describe("buildAuthHeaders — simple variants", () => {
  afterEach(() =>
    withEnv({
      [SEED_ENV]: undefined,
      [TOKEN_ENV]: undefined,
      RESOLVER_TEST_VAR: undefined,
    }),
  )

  it("returns empty headers for undefined auth", async () => {
    const h = await buildAuthHeaders(undefined, '{"x":1}')
    expect(h).toEqual({})
  })

  it("returns empty headers for type=none", async () => {
    const h = await buildAuthHeaders({ type: "none" }, '{"x":1}')
    expect(h).toEqual({})
  })

  it("returns Authorization for type=bearer", async () => {
    const h = await buildAuthHeaders({ type: "bearer", token: "abc" }, '{"x":1}')
    expect(h).toEqual({ Authorization: "Bearer abc" })
  })

  it("reads token from env for type=bearer_env", async () => {
    withEnv({ RESOLVER_TEST_VAR: "from-env" })
    const h = await buildAuthHeaders(
      { type: "bearer_env", envVar: "RESOLVER_TEST_VAR" },
      '{"x":1}',
    )
    expect(h).toEqual({ Authorization: "Bearer from-env" })
  })

  it("throws clear error when bearer_env var is unset", async () => {
    withEnv({ RESOLVER_TEST_VAR: undefined })
    await expect(
      buildAuthHeaders(
        { type: "bearer_env", envVar: "RESOLVER_TEST_VAR" },
        '{"x":1}',
      ),
    ).rejects.toThrow(/"RESOLVER_TEST_VAR" is not set/)
  })
})

describe("buildAuthHeaders — did_signed variant", () => {
  afterEach(() =>
    withEnv({
      [SEED_ENV]: undefined,
      [TOKEN_ENV]: undefined,
    }),
  )

  it("refuses to sign when identity is missing — clear error", async () => {
    withEnv({ [TOKEN_ENV]: "oauth-token-xyz" })
    await expect(
      buildAuthHeaders(
        { type: "did_signed", tokenEnvVar: TOKEN_ENV },
        '{"x":1}',
        /* identity */ undefined,
      ),
    ).rejects.toThrow(/did_signed peer requires a gateway LocalIdentity/)
  })

  it("refuses to sign when OAuth env var is unset — clear error", async () => {
    // Identity present, but token env unset
    withEnv({ [SEED_ENV]: Buffer.from(new Uint8Array(32)).toString("base64") })
    const identity = loadLocalIdentity({
      author: "ops@example.com",
      name: "gateway",
      seedEnvVar: SEED_ENV,
    })
    withEnv({ [TOKEN_ENV]: undefined })

    await expect(
      buildAuthHeaders(
        { type: "did_signed", tokenEnvVar: TOKEN_ENV },
        '{"x":1}',
        identity,
      ),
    ).rejects.toThrow(new RegExp(`"${TOKEN_ENV}" is not set`))
  })

  it("produces Authorization + three X-DID-* headers on happy path", async () => {
    withEnv({
      [SEED_ENV]: Buffer.from(new Uint8Array(32)).toString("base64"),
      [TOKEN_ENV]: "oauth-token-xyz",
    })
    const identity = loadLocalIdentity({
      author: "ops@example.com",
      name: "gateway",
      seedEnvVar: SEED_ENV,
    })

    const h = await buildAuthHeaders(
      { type: "did_signed", tokenEnvVar: TOKEN_ENV },
      '{"method":"message/send"}',
      identity,
    )

    expect(h.Authorization).toBe("Bearer oauth-token-xyz")
    expect(h["X-DID"]).toBe(identity.did)
    expect(h["X-DID-Timestamp"]).toMatch(/^\d+$/)
    expect(h["X-DID-Signature"]).toMatch(/^[1-9A-HJ-NP-Za-km-z]+$/) // base58
  })

  it("falls back to tokenProvider when tokenEnvVar is omitted", async () => {
    withEnv({ [SEED_ENV]: Buffer.from(new Uint8Array(32)).toString("base64") })
    const identity = loadLocalIdentity({
      author: "ops@example.com",
      name: "gateway",
      seedEnvVar: SEED_ENV,
    })

    let providerCalls = 0
    const fakeProvider = {
      async getToken() {
        providerCalls += 1
        return "auto-acquired-token"
      },
    }

    const h = await buildAuthHeaders(
      { type: "did_signed" /* no tokenEnvVar */ },
      '{"x":1}',
      identity,
      fakeProvider,
    )

    expect(h.Authorization).toBe("Bearer auto-acquired-token")
    expect(h["X-DID-Signature"]).toMatch(/^[1-9A-HJ-NP-Za-km-z]+$/)
    expect(providerCalls).toBe(1)
  })

  it("tokenEnvVar takes precedence over tokenProvider when both are set", async () => {
    withEnv({
      [SEED_ENV]: Buffer.from(new Uint8Array(32)).toString("base64"),
      [TOKEN_ENV]: "env-token",
    })
    const identity = loadLocalIdentity({
      author: "ops@example.com",
      name: "gateway",
      seedEnvVar: SEED_ENV,
    })

    const fakeProvider = {
      getToken: async () => "provider-token",
    }

    const h = await buildAuthHeaders(
      { type: "did_signed", tokenEnvVar: TOKEN_ENV },
      '{"x":1}',
      identity,
      fakeProvider,
    )

    // Explicit peer-scoped env var wins over gateway-wide provider.
    expect(h.Authorization).toBe("Bearer env-token")
  })

  it("refuses when neither tokenEnvVar nor tokenProvider is available", async () => {
    withEnv({ [SEED_ENV]: Buffer.from(new Uint8Array(32)).toString("base64") })
    const identity = loadLocalIdentity({
      author: "ops@example.com",
      name: "gateway",
      seedEnvVar: SEED_ENV,
    })

    await expect(
      buildAuthHeaders(
        { type: "did_signed" /* no tokenEnvVar */ },
        '{"x":1}',
        identity,
        /* tokenProvider */ undefined,
      ),
    ).rejects.toThrow(/BINDU_GATEWAY_HYDRA_TOKEN_URL/)
  })

  it("signs the exact body string passed in (regression guard)", async () => {
    // The load-bearing invariant: the body that gets signed is the
    // body the test passes — no re-serialization, no canonicalization.
    // If this ever regresses, the peer rejects with crypto_mismatch.
    withEnv({
      [SEED_ENV]: Buffer.from(new Uint8Array(32)).toString("base64"),
      [TOKEN_ENV]: "tok",
    })
    const identity = loadLocalIdentity({
      author: "ops@example.com",
      name: "gateway",
      seedEnvVar: SEED_ENV,
    })

    // Sign a specific body with a fixed timestamp via the low-level signer
    // directly, and separately via buildAuthHeaders — signatures should
    // agree when using the same fixed timestamp.
    const body = '{"weird":  "spacing"}' // deliberately unusual whitespace
    const ts = Math.floor(Date.now() / 1000)
    const directSig = await identity.sign(body, ts)

    // Freeze Date.now so buildAuthHeaders uses the same timestamp
    const originalNow = Date.now
    Date.now = () => ts * 1000
    try {
      const fromResolver = await buildAuthHeaders(
        { type: "did_signed", tokenEnvVar: TOKEN_ENV },
        body,
        identity,
      )
      expect(fromResolver["X-DID-Signature"]).toBe(directSig["X-DID-Signature"])
      expect(fromResolver["X-DID-Timestamp"]).toBe(directSig["X-DID-Timestamp"])
    } finally {
      Date.now = originalNow
    }
  })
})
