---
id: 2026-04-18-compaction-mid-turn-cut
title: Compaction split landed mid-turn, breaking tool_use/tool_result pairing
severity: critical
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: gateway/session
commit: 77603da
---

## Symptom

Sessions that hit the compaction threshold during a tool-heavy turn
permanently broke. The very next request to the model failed with:

```
messages.N.content.0: tool_use id "toolu_…" does not have a
corresponding tool_result
```

(or the equivalent OpenAI error). The session was stuck — the planner
couldn't retry around it, because the DB state was already wrong: some
messages were flagged `compacted=true`, so even a fresh turn would
rebuild the same broken message list. Only manual intervention
(resetting the flag) recovered the session.

## Root cause

`splitHead` in `gateway/src/session/compaction.ts:62-71` (pre-fix):

```ts
function splitHead(history, keepTail) {
  if (history.length <= keepTail) return { head: [], tail: history }
  return {
    head: history.slice(0, history.length - keepTail),
    tail: history.slice(history.length - keepTail),
  }
}
```

The cut was a raw message-count slice. A single planner turn spans many
messages — user + assistant-with-`tool_use` + `tool_result` + possibly
more tool pairs + final-assistant. A three-tool turn is 8 messages. A
ten-tool turn is 22.

With `keepTail = 4`, the cut landed mid-turn at least half the time
a turn was long enough to cross the boundary. The common failing shape:

```
head: [..., assistant(tool_use, id=X), tool(result, refs=X), assistant(tool_use, id=Y)]
tail: [tool(result, refs=Y), assistant(final)]                          ← Y's tool_use is in head
```

The provider sees a `tool_result` in the visible message list (tail) that
references a `tool_use` id that doesn't appear anywhere (head was
replaced by the summary paragraph). Hard 400 error, unrecoverable
without touching the DB.

Mental model that led to the bug: `keepTail` was thought of as "keep the
last N messages verbatim," with N chosen to be roughly one short turn.
The assumption was that a turn is 2–3 messages. Reality is 8–22 for
tool-heavy turns, which were the whole point of this gateway.

## Fix

Walk left from the naive cut point until the message at the split is
a `user` turn. Since a user message starts a new turn by definition,
the invariant is that every assistant `tool_use` is in the same half
as its `tool_result`.

```ts
let cut = history.length - minKeepTail
while (cut > 0 && history[cut].info.role !== "user") {
  cut -= 1
}
if (cut === 0) return { head: [], tail: history }   // one unbroken turn
return { head: history.slice(0, cut), tail: history.slice(cut) }
```

`keepTail` is now a MINIMUM, not an exact count. Tail may be longer
than requested — never shorter.

See commit [77603da](../../commit/77603da) and five regression cases in
`gateway/tests/session/compaction-split.test.ts` covering tool-heavy
turns, single-unbroken-turn histories, and boundary cases.

## Why the tests didn't catch it

`splitHead` was an un-exported helper and had no unit tests. Compaction
as a whole had no tests. The bug only fires when:

1. Token budget crosses the threshold during a session — a *statistical*
   event that depends on session content.
2. The cut point lands inside a turn — another statistical event.

Both conditions are non-deterministic with respect to any single test
run. A dev running a short test or a short demo would never hit it.
Production would hit it regularly, and when it hit, it killed the
session permanently — so the signal would have been "customer reports
weird errors in long sessions" which is hard to reproduce locally
without a data harness.

The class of bug also requires thinking about the *API contract* of the
downstream LLM, not just our own code. Nothing in our types or Zod
schemas tells us that `tool_use` + `tool_result` must be paired in the
visible message list — that rule lives in Anthropic's and OpenAI's API
docs. Our tests cover our code's behavior; they don't cover our
compliance with external contracts.

## Class of bug — where else to watch

**"Index arithmetic on a list with semantic boundaries"** — any time
code slices, splits, or truncates a message list by count, it must
respect turn boundaries (and, more strictly, tool-pair boundaries).
Candidates for similar bugs in the codebase:

- `gateway/src/session/index.ts:listMessages` paginates at 1000 rows.
  If a long session's boundary falls mid-turn, and some code path
  uses the truncated list directly with the LLM, same failure mode.
  Tracked in [`known-issues.md`](../known-issues.md) under
  `list-messages-pagination-silent`.
- Revert (`gateway/src/session/revert.ts`) cuts by `created_at`
  timestamp. Timestamps generally align with turn starts (user
  messages precede assistant responses), but there's no enforced
  invariant. Worth auditing.
- Any future "replay from turn N" or "export last K turns" feature
  must slice on user-message boundaries, not message indices.

The broader rule: **if an API contract requires that messages of type
A must pair with messages of type B, a slice operation must always
leave those pairs whole.** The fix approach here — walk to the
nearest semantic boundary — generalizes. When the semantic unit is
"a turn," the boundary is a user message. When the semantic unit is
"a tool pair," the boundary is a matching `tool_result`.

A minor related lesson: **`keepTail` as an exact count was the wrong
vocabulary.** The name suggested strict guarantees that were unsafe.
Renaming it to `minKeepTail` in the fix makes the looser contract
visible in the API. When a parameter semantically means "at least this
many," name it `minX` — don't rely on docstrings.
