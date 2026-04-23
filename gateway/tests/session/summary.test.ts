import { describe, it, expect, vi, beforeEach } from "vitest"

/**
 * Regression test for the "lossy second-pass compaction" bug.
 *
 * Before the fix:
 *   - `summarize()` ignored any prior summary; it only looked at the
 *     new head messages.
 *   - Each compaction pass therefore produced a summary of ONLY what
 *     happened since the previous pass, and the DB UPDATE overwrote
 *     the prior summary wholesale.
 *   - Facts captured in pass #1 (early user goals, early agent results,
 *     translations, etc.) silently vanished from session context.
 *
 * The fix (src/session/summary.ts + src/session/compaction.ts):
 *   - summarize() accepts an optional `priorSummary?: string | null`.
 *     When present, it's injected as a user message with a
 *     "[PRIOR SUMMARY — preserve every fact below]" marker so the
 *     model is explicitly told to carry facts forward.
 *   - compaction.runCompaction reads `compaction_summary` from the
 *     session row before summarizing and passes it through.
 *   - The system prompt gained explicit "new summary must be a SUPERSET"
 *     language.
 *
 * This file tests the summary.ts plumbing. We mock ai's `generateText`
 * (no real LLM call) and inspect the message list + system prompt that
 * would be sent.
 */

const generateTextMock = vi.fn()

vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai")
  return {
    ...actual,
    generateText: (...args: unknown[]) => generateTextMock(...args),
  }
})

// Import AFTER the mock so summarize() binds to the stub.
import { summarize } from "../../src/session/summary"
import type { MessageWithParts } from "../../src/session/message"

describe("summarize()", () => {
  beforeEach(() => {
    generateTextMock.mockReset()
    generateTextMock.mockResolvedValue({ text: "  stub summary  " })
  })

  const fakeLlm = {} as any  // generateText is mocked so the handle is never inspected
  const mkUserMsg = (id: string, text: string): MessageWithParts => ({
    info: { id: id as any, sessionID: "s" as any, role: "user", time: { created: 0 } },
    parts: [{ id: `${id}-p` as any, type: "text", text, time: { start: 0 } }],
  })

  it("without priorSummary, sends no PRIOR SUMMARY marker", async () => {
    const out = await summarize({
      model: fakeLlm,
      messagesToCompact: [mkUserMsg("m1", "turn 1"), mkUserMsg("m2", "turn 2")],
    })
    expect(out).toBe("stub summary")

    expect(generateTextMock).toHaveBeenCalledTimes(1)
    const call = generateTextMock.mock.calls[0][0] as {
      system: string
      messages: Array<{ role: string; content: string }>
    }

    const joinedContent = call.messages
      .map((m) => (typeof m.content === "string" ? m.content : JSON.stringify(m.content)))
      .join(" || ")
    expect(joinedContent).not.toContain("PRIOR SUMMARY")

    // The closing prompt is the one-shot variant (no superset language).
    const last = call.messages[call.messages.length - 1]
    expect(typeof last.content === "string" && last.content).toMatch(/Summarize the above session history/i)
  })

  it("with priorSummary, injects a PRIOR SUMMARY marker BEFORE the history", async () => {
    const prior =
      "User asked about AWD EVs. Research found Tesla Model Y. Translator returned テスラ モデル Y for Tesla."

    await summarize({
      model: fakeLlm,
      messagesToCompact: [mkUserMsg("m3", "turn 3"), mkUserMsg("m4", "turn 4")],
      priorSummary: prior,
    })

    expect(generateTextMock).toHaveBeenCalledTimes(1)
    const call = generateTextMock.mock.calls[0][0] as {
      system: string
      messages: Array<{ role: string; content: unknown }>
    }

    // First message must be the prior-summary marker, and must contain
    // every load-bearing fact from the prior summary verbatim.
    const first = call.messages[0]
    expect(first.role).toBe("user")
    expect(typeof first.content === "string" && first.content).toContain("PRIOR SUMMARY")
    expect(typeof first.content === "string" && first.content).toContain("Tesla Model Y")
    expect(typeof first.content === "string" && first.content).toContain("テスラ モデル Y")

    // The closing prompt MUST tell the model this is a union / superset,
    // not a fresh summary.
    const last = call.messages[call.messages.length - 1]
    const lastText = typeof last.content === "string" ? last.content : ""
    expect(lastText).toMatch(/superset/i)
    expect(lastText).toMatch(/PRIOR SUMMARY/)

    // System prompt must include the fact-preservation clause.
    expect(call.system).toMatch(/PRIOR SUMMARY/)
    expect(call.system).toMatch(/SUPERSET/)
    expect(call.system).toMatch(/preserve every named entity/i)
  })

  it("treats empty / whitespace priorSummary as absent", async () => {
    await summarize({
      model: fakeLlm,
      messagesToCompact: [mkUserMsg("m5", "turn 5")],
      priorSummary: "   \n  ",
    })

    const call = generateTextMock.mock.calls[0][0] as {
      messages: Array<{ content: unknown }>
    }
    const joined = call.messages
      .map((m) => (typeof m.content === "string" ? m.content : JSON.stringify(m.content)))
      .join(" || ")
    expect(joined).not.toContain("PRIOR SUMMARY")
  })
})
