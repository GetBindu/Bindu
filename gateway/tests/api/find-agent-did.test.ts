import { describe, it, expect } from "vitest"
import { findAgentDID } from "../../src/api/plan-route"
import type { PlanRequest } from "../../src/planner"

/**
 * Precedence test for `findAgentDID` — the resolver that decides which
 * DID (and which provenance label) lands on each task.* SSE frame.
 *
 * Covers the fix for the "SSE agent_did doesn't surface observed DIDs"
 * bug (BUGS_AND_KNOWN_ISSUES.md). Before: the helper only read
 * `trust.pinnedDID`, so any caller that didn't pin saw `agent_did:
 * null` even after fetchAgentCard had observed the peer's real DID.
 * After: observed DIDs are the fallback, with `source` distinguishing
 * the two.
 */

const DID_PINNED = "did:bindu:ops_at_example_com:research:pinned-11111111"
const DID_OBSERVED = "did:bindu:ops_at_example_com:research:observed-22222222"

const mkRequest = (pinnedFor: Record<string, string | undefined> = {}): PlanRequest =>
  ({
    question: "test",
    agents: Object.entries(pinnedFor).map(([name, pinned]) => ({
      name,
      endpoint: `http://${name}.local`,
      skills: [],
      ...(pinned ? { trust: { pinnedDID: pinned } } : {}),
    })),
  }) as PlanRequest

describe("findAgentDID — DID precedence and provenance", () => {
  it("returns {did: pinned, source: 'pinned'} when pinnedDID is set, even if observed also exists", () => {
    const req = mkRequest({ research: DID_PINNED })
    const observed = new Map([["research", DID_OBSERVED]])

    expect(findAgentDID(req, observed, "research")).toEqual({
      did: DID_PINNED,
      source: "pinned",
    })
  })

  it("returns {did: observed, source: 'observed'} when pinnedDID is absent but observed exists", () => {
    const req = mkRequest({ research: undefined })
    const observed = new Map([["research", DID_OBSERVED]])

    expect(findAgentDID(req, observed, "research")).toEqual({
      did: DID_OBSERVED,
      source: "observed",
    })
  })

  it("returns {did: null, source: null} when neither path resolves", () => {
    const req = mkRequest({ research: undefined })
    const observed = new Map<string, string>()

    expect(findAgentDID(req, observed, "research")).toEqual({
      did: null,
      source: null,
    })
  })

  it("returns {did: null, source: null} when the agent name isn't in the catalog at all", () => {
    // The planner's `load_recipe` tool passes through this helper with
    // agentName = "load_recipe" — never in the catalog, should cleanly
    // resolve to null/null rather than throwing.
    const req = mkRequest({ research: DID_PINNED })
    const observed = new Map([["research", DID_OBSERVED]])

    expect(findAgentDID(req, observed, "load_recipe")).toEqual({
      did: null,
      source: null,
    })
  })

  it("pinned precedence is per-agent — one agent can be pinned while another is observed", () => {
    const req = mkRequest({ research: DID_PINNED, math: undefined })
    const observed = new Map([
      ["research", DID_OBSERVED],
      ["math", "did:bindu:ops_at_example_com:math:observed-3333"],
    ])

    const r = findAgentDID(req, observed, "research")
    const m = findAgentDID(req, observed, "math")

    expect(r.source).toBe("pinned")
    expect(r.did).toBe(DID_PINNED)
    expect(m.source).toBe("observed")
    expect(m.did).toBe("did:bindu:ops_at_example_com:math:observed-3333")
  })

  it("observed-DID map is treated as authoritative for observed claims — does not cross-contaminate across names", () => {
    const req = mkRequest({ "a": undefined, "b": undefined })
    const observed = new Map([["a", DID_OBSERVED]])

    expect(findAgentDID(req, observed, "a").did).toBe(DID_OBSERVED)
    expect(findAgentDID(req, observed, "b").did).toBeNull()
  })
})
