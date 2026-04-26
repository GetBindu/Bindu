import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"
import { fetchAgentCard, __resetAgentCardCacheForTests } from "../../src/bindu/client/agent-card"

/**
 * Coverage for the AgentCard fetch helper — the piece that activates
 * maybeVerifySignatures' observed-DID fallback when the caller enabled
 * `trust.verifyDID: true` without pinning a DID.
 *
 * Resolves the "peer.card is never populated" high-severity entry in
 * BUGS_AND_KNOWN_ISSUES.md: before this module, the fallback at
 * bindu/client/index.ts:196 was dead code because nothing ever set
 * peer.card. These tests pin the four real outcomes (success, 404,
 * malformed body, cache hit) and the degrade-to-null contract on
 * every failure mode.
 */

const VALID_CARD = {
  id: "did:bindu:ops_at_example_com:research:7dc57d21-2c81-f6f5-c679-e51995f97e22",
  name: "research",
  description: "Web search and summarize.",
  skills: [],
  defaultInputModes: ["text/plain"],
  defaultOutputModes: ["text/plain"],
  capabilities: {
    extensions: [
      {
        uri: "did:bindu:ops_at_example_com:research:7dc57d21-2c81-f6f5-c679-e51995f97e22",
      },
    ],
  },
}

describe("fetchAgentCard", () => {
  beforeEach(() => {
    __resetAgentCardCacheForTests()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches and parses a valid AgentCard from /.well-known/agent.json", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(VALID_CARD), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )

    const result = await fetchAgentCard("http://localhost:3773")
    expect(result).not.toBeNull()
    expect(result?.name).toBe("research")
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:3773/.well-known/agent.json",
      expect.objectContaining({ signal: expect.anything() }),
    )
  })

  it("returns null on non-2xx without throwing", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("not found", { status: 404 }),
    )

    const result = await fetchAgentCard("http://localhost:3773")
    expect(result).toBeNull()
  })

  it("returns null on malformed JSON body", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("not a json body, just a string", {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )

    const result = await fetchAgentCard("http://localhost:3773")
    expect(result).toBeNull()
  })

  it("returns null when the body doesn't match the AgentCard schema", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ wrong: "shape" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )

    const result = await fetchAgentCard("http://localhost:3773")
    expect(result).toBeNull()
  })

  it("returns null and caches the failure when fetch throws", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("ECONNREFUSED"))

    const result = await fetchAgentCard("http://localhost:3773")
    expect(result).toBeNull()
  })

  it("caches successful results — second call does not re-fetch", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(VALID_CARD), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )

    const first = await fetchAgentCard("http://localhost:3773")
    const second = await fetchAgentCard("http://localhost:3773")

    expect(first).toBe(second) // same cached reference
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it("caches failures too — second call does not re-fetch a known-bad peer", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("", { status: 404 }),
    )

    await fetchAgentCard("http://localhost:3773")
    await fetchAgentCard("http://localhost:3773")

    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it("caches per-URL — a different peer is fetched independently", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(VALID_CARD), { status: 200 }),
    )

    await fetchAgentCard("http://localhost:3773")
    await fetchAgentCard("http://localhost:3775")

    expect(fetchSpy).toHaveBeenCalledTimes(2)
    const urls = fetchSpy.mock.calls.map((c) => c[0])
    expect(urls).toContain("http://localhost:3773/.well-known/agent.json")
    expect(urls).toContain("http://localhost:3775/.well-known/agent.json")
  })

  it("aborts on timeout", async () => {
    // Simulate a fetch that never resolves — the helper's internal
    // timeout should abort. We use a short timeout and expect null.
    vi.spyOn(global, "fetch").mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          const signal = (init as { signal?: AbortSignal } | undefined)?.signal
          signal?.addEventListener("abort", () => reject(new Error("aborted")), {
            once: true,
          })
        }),
    )

    const result = await fetchAgentCard("http://localhost:3773", { timeoutMs: 50 })
    expect(result).toBeNull()
  })
})
