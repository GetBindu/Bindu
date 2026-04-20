import { describe, it, expect } from "vitest"
import { deriveAuthor, deriveGatewayId, splitModelId } from "../../src/api/health-route"

/**
 * Unit coverage for the /health helpers. These are the bits the full
 * handler would be hard to exercise without spinning up the whole layer
 * graph — pinning them here catches the regressions most likely to ship
 * subtly wrong (a DID-segment off by one, a model-id split that drops
 * the provider slash).
 *
 * The handler itself is a closure over service state built at boot, so
 * the cheapest integration test is `npm run dev && curl /health` — we
 * rely on that plus these unit tests rather than a full layer mock.
 */

describe("splitModelId", () => {
  it("splits the first slash only, preserving nested provider paths", () => {
    expect(splitModelId("openrouter/anthropic/claude-sonnet-4.6")).toEqual({
      provider: "openrouter",
      modelId: "anthropic/claude-sonnet-4.6",
    })
  })

  it("returns provider=null when the string has no slash (degenerate config)", () => {
    expect(splitModelId("gpt-4o")).toEqual({ provider: null, modelId: "gpt-4o" })
  })

  it("returns both null when input is null", () => {
    expect(splitModelId(null)).toEqual({ provider: null, modelId: null })
  })
})

describe("deriveGatewayId", () => {
  it("returns the last segment (agent_id) for did:bindu", () => {
    expect(
      deriveGatewayId("did:bindu:ops_at_example_com:gateway:f72ba681-f873-324c-6012-23c4d5b72451"),
    ).toBe("f72ba681-f873-324c-6012-23c4d5b72451")
  })

  it("returns the multibase portion for did:key", () => {
    expect(deriveGatewayId("did:key:z6Mk...")).toBe("z6Mk...")
  })

  it("returns null for malformed/missing DIDs", () => {
    expect(deriveGatewayId(undefined)).toBeNull()
    expect(deriveGatewayId("")).toBeNull()
    expect(deriveGatewayId("not-a-did")).toBeNull()
    expect(deriveGatewayId("did:bindu:only-one-segment")).toBeNull()
  })
})

describe("deriveAuthor", () => {
  it("returns the author segment for did:bindu", () => {
    expect(
      deriveAuthor("did:bindu:ops_at_example_com:gateway:f72ba681-f873-324c-6012-23c4d5b72451"),
    ).toBe("ops_at_example_com")
  })

  it("returns null for did:key (no author concept)", () => {
    expect(deriveAuthor("did:key:z6Mk...")).toBeNull()
  })

  it("returns null for missing/malformed DIDs", () => {
    expect(deriveAuthor(undefined)).toBeNull()
    expect(deriveAuthor("")).toBeNull()
    expect(deriveAuthor("something-random")).toBeNull()
  })
})
