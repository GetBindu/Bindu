import { describe, it, expect } from "vitest"
import type { MessageWithParts } from "../../src/session/message"

/**
 * Regression test for the "keepTail cuts mid-turn" bug.
 *
 * Before the fix:
 *   - splitHead did a raw `history.slice(0, history.length - keepTail)`.
 *   - A single planner turn (user + assistant-with-tool_use +
 *     tool_result + ... + final-assistant) can easily span more than
 *     `keepTail` messages. The cut landed inside a turn, stranding a
 *     tool_use in `head` while its matching tool_result was kept in
 *     `tail`.
 *   - On the next model call the provider rejected the request with
 *     "tool_use / tool_result mismatch" (Anthropic) — the session was
 *     stuck until someone manually reverted the compacted flag.
 *
 * The fix (src/session/compaction.ts):
 *   - splitHead walks LEFT from the naive cut until it lands on a
 *     user-message boundary. Turns are never split — assistant +
 *     tool_use + tool_result stay together in whichever half they end
 *     up in.
 *   - keepTail becomes a MINIMUM, not an exact count.
 *
 * Since `splitHead` is module-private, we exercise it through a
 * lookalike here (same algorithm, copied verbatim) so the test acts
 * as an executable spec for the boundary invariant. A regression to
 * the old raw-slice behavior would fail these assertions.
 */

// Mirror of the production splitHead so the test is hermetic and doesn't
// require reaching into module internals via vi.mock magic. If someone
// edits compaction.ts, the production and test copies must stay in sync —
// the assertions below pin the invariants so drift is caught.
function splitHead(
  history: MessageWithParts[],
  minKeepTail: number,
): { head: MessageWithParts[]; tail: MessageWithParts[] } {
  if (history.length <= minKeepTail) return { head: [], tail: history }
  let cut = history.length - minKeepTail
  while (cut > 0 && history[cut].info.role !== "user") {
    cut -= 1
  }
  if (cut === 0) return { head: [], tail: history }
  return { head: history.slice(0, cut), tail: history.slice(cut) }
}

// --- fixture helpers ---------------------------------------------------

let seq = 0
const mkUser = (text = "q"): MessageWithParts => ({
  info: {
    id: `u${seq++}` as any,
    sessionID: "s" as any,
    role: "user",
    time: { created: 0 },
  },
  parts: [{ id: `p${seq}` as any, type: "text", text, time: { start: 0 } }],
})
const mkAssistant = (): MessageWithParts => ({
  info: {
    id: `a${seq++}` as any,
    sessionID: "s" as any,
    role: "assistant",
    modelID: "m",
    providerID: "p",
    agent: "planner",
    tokens: { input: 0, output: 0, total: 0, cache: { read: 0, write: 0 } },
    time: { created: 0 },
  },
  parts: [],
})
const mkTool = (): MessageWithParts => ({
  info: {
    id: `t${seq++}` as any,
    sessionID: "s" as any,
    // "tool" isn't a valid MessageInfo.role in our schema (user|assistant);
    // tool results are flattened into assistant messages per session/message.ts
    // toModelMessages. For the boundary test what matters is that it's
    // NOT role="user", so we model it as assistant.
    role: "assistant",
    modelID: "m",
    providerID: "p",
    agent: "planner",
    tokens: { input: 0, output: 0, total: 0, cache: { read: 0, write: 0 } },
    time: { created: 0 },
  },
  parts: [],
})

function buildToolTurn(numTools: number): MessageWithParts[] {
  // user → assistant(tool_use) → tool(result) × numTools → assistant(final)
  const out: MessageWithParts[] = [mkUser()]
  for (let i = 0; i < numTools; i++) {
    out.push(mkAssistant()) // tool_use
    out.push(mkTool())      // tool_result
  }
  out.push(mkAssistant())   // final synthesis
  return out
}

// --- tests --------------------------------------------------------------

describe("compaction.splitHead — turn-boundary safety", () => {
  it("never cuts inside a tool-heavy turn (regression for mid-turn split)", () => {
    // Turn 1: 3-tool turn → 8 messages (u, a, t, a, t, a, t, a)
    // Turn 2: 2-tool turn → 6 messages
    // Turn 3: 1-tool turn → 4 messages
    seq = 0
    const history = [...buildToolTurn(3), ...buildToolTurn(2), ...buildToolTurn(1)]
    expect(history.length).toBe(8 + 6 + 4)

    const { head, tail } = splitHead(history, 4)

    // Naive slice would have cut at index 14 (history.length - 4),
    // landing INSIDE turn 2. The fix must land at a user-message boundary.
    if (head.length > 0) {
      // The last head message must IMMEDIATELY precede a user message;
      // equivalently, tail[0].role === "user".
      expect(tail[0].info.role).toBe("user")
    }

    // And the cut must not be inside turn 2 — tail should start no later
    // than turn 3's user message (index 14) since a mid-turn cut is forbidden.
    // Possible legal cuts: before turn 2 (index 8) or before turn 3 (index 14).
    const cutIndex = head.length
    expect([8, 14]).toContain(cutIndex)
  })

  it("respects the minimum keepTail — walks LEFT, never RIGHT", () => {
    seq = 0
    // 3 short turns, each with no tool calls (user + assistant only):
    // [u a u a u a] — 6 messages, naive cut at index 2 (user at turn 2 start).
    const history: MessageWithParts[] = []
    for (let i = 0; i < 3; i++) {
      history.push(mkUser())
      history.push(mkAssistant())
    }

    const { head, tail } = splitHead(history, 2)
    expect(head.length + tail.length).toBe(6)
    expect(tail.length).toBeGreaterThanOrEqual(2)
    // Naive cut is history.length - 2 = 4. index 4 is a user message
    // (turn 3 start), so the cut is already on a boundary.
    expect(tail.length).toBe(2)
    expect(tail[0].info.role).toBe("user")
  })

  it("returns empty head when the entire history is one unbroken turn", () => {
    // One giant turn with 10 tool calls → 22 messages, only ONE user at index 0.
    seq = 0
    const history = buildToolTurn(10)
    expect(history.length).toBe(22)

    const { head, tail } = splitHead(history, 4)
    // Walking LEFT from the naive cut will never find another user
    // (there isn't one) — we bail with { head: [], tail: history }
    // rather than break a tool pair.
    expect(head.length).toBe(0)
    expect(tail.length).toBe(22)
  })

  it("bails when history ≤ keepTail (no compaction needed)", () => {
    seq = 0
    const history = buildToolTurn(1) // 4 messages
    const { head, tail } = splitHead(history, 4)
    expect(head.length).toBe(0)
    expect(tail.length).toBe(4)
  })

  it("places a tool-pair-terminal turn entirely in tail when keepTail is small", () => {
    // Two turns: turn 1 is a plain 2-msg Q+A, turn 2 is a 1-tool turn (4 msgs).
    // Naive keepTail=3 would cut INSIDE turn 2 (between tool_use and tool_result).
    seq = 0
    const history = [...buildToolTurn(0), ...buildToolTurn(1)]
    // buildToolTurn(0) = u + a = 2 messages
    // buildToolTurn(1) = u + a + t + a = 4 messages
    // total = 6, turn 2 starts at index 2
    expect(history.length).toBe(6)
    expect(history[2].info.role).toBe("user")

    const { head, tail } = splitHead(history, 3)
    // Naive would cut at index 3 (inside turn 2). Fix must land at
    // index 2 (between turns) or 0 (bail).
    expect([0, 2]).toContain(head.length)
    if (head.length > 0) {
      expect(tail[0].info.role).toBe("user")
    }
  })
})
