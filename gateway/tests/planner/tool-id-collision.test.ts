import { describe, it, expect } from "vitest"
import { findDuplicateToolIds, normalizeToolName, type AgentRequest } from "../../src/planner"

/**
 * Tool-id collision detection — protects against silent last-write-wins
 * when two catalog entries would produce the same normalized tool id.
 *
 * Before this guard, session/prompt.ts's `toolMap[id] = ai` assignment
 * silently let the later entry overwrite the earlier one. A caller who
 * thought they were load-balancing across two peers saw only one being
 * called, with no indication which.
 */

const mk = (name: string, skillIds: string[]): AgentRequest => ({
  name,
  endpoint: "http://example.com",
  skills: skillIds.map((id) => ({ id })),
})

describe("findDuplicateToolIds", () => {
  it("returns null for a clean catalog", () => {
    expect(findDuplicateToolIds([mk("a", ["x"]), mk("b", ["y"])])).toBeNull()
  })

  it("returns null for same skill ids on DIFFERENT agent names (not a collision)", () => {
    // call_research_a_search vs call_research_b_search — distinct tool ids.
    expect(
      findDuplicateToolIds([mk("research_a", ["search"]), mk("research_b", ["search"])]),
    ).toBeNull()
  })

  it("flags two entries with the same agent name AND skill id", () => {
    const got = findDuplicateToolIds([mk("research", ["search"]), mk("research", ["search"])])
    expect(got).not.toBeNull()
    expect(got![0].toolId).toBe("call_research_search")
    expect(got![0].entries).toHaveLength(2)
  })

  it("flags a single agent with a duplicated skill id in its skills[]", () => {
    const got = findDuplicateToolIds([mk("research", ["search", "search"])])
    expect(got).not.toBeNull()
    expect(got![0].entries).toHaveLength(2)
    expect(got![0].entries.every((e) => e.agentName === "research" && e.skillId === "search")).toBe(
      true,
    )
  })

  it("flags non-alphanumeric chars that flatten to the same normalized id", () => {
    // normalizeToolName replaces `.` and `-` with `_` — so foo.bar and foo-bar
    // both become foo_bar and collide with foo_bar.
    const got = findDuplicateToolIds([
      mk("foo.bar", ["x"]),
      mk("foo_bar", ["x"]),
    ])
    expect(got).not.toBeNull()
    expect(got![0].toolId).toBe(normalizeToolName("call_foo.bar_x"))
    expect(got![0].toolId).toBe(normalizeToolName("call_foo_bar_x"))
  })

  it("returns ALL colliding groups, not just the first", () => {
    const got = findDuplicateToolIds([
      mk("a", ["x", "x"]), // collision group 1
      mk("b", ["y", "y"]), // collision group 2
      mk("c", ["z"]), // clean
    ])
    expect(got).not.toBeNull()
    expect(got!).toHaveLength(2)
    const toolIds = got!.map((c) => c.toolId).sort()
    expect(toolIds).toEqual(["call_a_x", "call_b_y"])
  })

  it("an agent with zero skills produces no tool ids (not a collision)", () => {
    expect(findDuplicateToolIds([mk("empty", []), mk("empty", [])])).toBeNull()
  })
})

describe("normalizeToolName", () => {
  it("replaces non-alphanumeric chars with underscores", () => {
    expect(normalizeToolName("call_foo.bar-baz_qux")).toBe("call_foo_bar_baz_qux")
  })

  it("truncates to 80 chars so runaway catalog entries don't produce absurd ids", () => {
    const long = "call_" + "x".repeat(200)
    expect(normalizeToolName(long).length).toBe(80)
  })

  it("is a pure function — same input always produces same output", () => {
    const a = normalizeToolName("call_research.agent_search-skill")
    const b = normalizeToolName("call_research.agent_search-skill")
    expect(a).toBe(b)
  })
})
