/**
 * Schema contract tests for the external /plan API.
 *
 * These guard two drift bugs the gateway_test_fleet exercise surfaced:
 *
 *   1. ``PeerAuthRequest`` was missing the ``did_signed`` variant even
 *      though ``PeerAuth`` in ``bindu/auth/resolver.ts`` had it. Every
 *      ``/plan`` request that tried to use DID signing got a 400 at
 *      the API boundary before the transport could run.
 *
 *   2. ``PlanPreferences`` keys were camelCase (``maxSteps``,
 *      ``timeoutMs``, ``responseFormat``) but the documented external
 *      API in ``gateway/plans/PLAN.md`` uses snake_case
 *      (``max_steps``, ``timeout_ms``, ``response_format``).
 *      ``.passthrough()`` kept the request valid but dropped the
 *      values on the floor — ``request.preferences?.maxSteps`` was
 *      always undefined for docs-compliant clients, so the planner
 *      silently ignored the cap.
 *
 * Both schemas belong to a published external contract. Tests live
 * here so any future drift between the schema and what callers send
 * (or what internal code reads) fails at unit-test time instead of
 * during an integration run.
 */

import { describe, it, expect } from "vitest"
import { PlanRequest, PlanPreferences, PeerAuthRequest } from "../../src/planner"

describe("PeerAuthRequest — external /plan API auth shape", () => {
  it("accepts type=none", () => {
    expect(PeerAuthRequest.safeParse({ type: "none" }).success).toBe(true)
  })

  it("accepts type=bearer with a token", () => {
    expect(
      PeerAuthRequest.safeParse({ type: "bearer", token: "abc" }).success,
    ).toBe(true)
  })

  it("accepts type=bearer_env with an envVar", () => {
    expect(
      PeerAuthRequest.safeParse({ type: "bearer_env", envVar: "MY_TOKEN" })
        .success,
    ).toBe(true)
  })

  it("accepts type=did_signed with no other fields (auto-token path)", () => {
    // did_signed without tokenEnvVar means "use the gateway's own
    // auto-acquired Hydra token." Common case, MUST be accepted.
    expect(PeerAuthRequest.safeParse({ type: "did_signed" }).success).toBe(
      true,
    )
  })

  it("accepts type=did_signed with a tokenEnvVar (federated path)", () => {
    expect(
      PeerAuthRequest.safeParse({
        type: "did_signed",
        tokenEnvVar: "PEER_A_TOKEN",
      }).success,
    ).toBe(true)
  })

  it("rejects unknown auth types", () => {
    expect(
      PeerAuthRequest.safeParse({ type: "magic", sauce: "abc" } as any).success,
    ).toBe(false)
  })

  it("rejects bearer without a token", () => {
    expect(PeerAuthRequest.safeParse({ type: "bearer" } as any).success).toBe(
      false,
    )
  })

  it("rejects did_signed with a non-string tokenEnvVar", () => {
    expect(
      PeerAuthRequest.safeParse({
        type: "did_signed",
        tokenEnvVar: 42,
      } as any).success,
    ).toBe(false)
  })
})

describe("PlanPreferences — keys must be snake_case (matches PLAN.md)", () => {
  it("accepts the documented snake_case keys", () => {
    const parsed = PlanPreferences.parse({
      response_format: "markdown",
      max_hops: 5,
      timeout_ms: 30_000,
      max_steps: 10,
    })
    expect(parsed.max_steps).toBe(10)
    expect(parsed.timeout_ms).toBe(30_000)
  })

  it("ignores camelCase keys (they become passthrough extras, not typed)", () => {
    // .passthrough() keeps unknown keys; they just don't satisfy the
    // typed fields. This guards against anyone "fixing" the schema by
    // adding camelCase aliases — the typed field must remain snake_case.
    const parsed = PlanPreferences.parse({ maxSteps: 42 })
    expect((parsed as { max_steps?: number }).max_steps).toBeUndefined()
  })

  it("is allowed to be empty", () => {
    expect(PlanPreferences.parse({})).toEqual({})
  })

  it("rejects non-positive max_steps", () => {
    expect(PlanPreferences.safeParse({ max_steps: 0 }).success).toBe(false)
    expect(PlanPreferences.safeParse({ max_steps: -5 }).success).toBe(false)
  })
})

describe("PlanRequest — full end-to-end shape a docs-compliant client sends", () => {
  it("parses a realistic did_signed + snake_case preferences request", () => {
    const request = {
      question: "What's the weather in Tokyo?",
      agents: [
        {
          name: "weather",
          endpoint: "https://weather.example.com",
          auth: { type: "did_signed" as const },
          skills: [
            {
              id: "forecast",
              description: "Get current weather",
            },
          ],
        },
      ],
      preferences: {
        response_format: "markdown",
        timeout_ms: 60_000,
        max_steps: 5,
      },
    }

    const parsed = PlanRequest.parse(request)
    expect(parsed.agents[0].auth).toEqual({ type: "did_signed" })
    expect(parsed.preferences?.max_steps).toBe(5)
  })

  it("parses a minimal request — empty agents, no preferences", () => {
    const parsed = PlanRequest.parse({
      question: "anything",
    })
    expect(parsed.question).toBe("anything")
    expect(parsed.agents).toEqual([])
  })

  it("rejects a request missing question", () => {
    expect(PlanRequest.safeParse({ agents: [] } as any).success).toBe(false)
  })
})
