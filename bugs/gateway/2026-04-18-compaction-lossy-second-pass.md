---
id: 2026-04-18-compaction-lossy-second-pass
title: Session compaction overwrote prior summary, progressively losing facts
severity: critical
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: gateway/session
commit: bbb1474
---

## Symptom

Long multi-agent sessions progressively forgot early context. After the
first compaction pass, facts captured in that summary (user's original
goal, early agent results, pinned translations, entity names) were
preserved correctly. After the second pass, those facts silently
disappeared — the planner could no longer reference them, gave
"I don't know" answers, or hallucinated replacements.

Observable only on sessions long enough to trigger two or more
compactions. Pattern: session starts coherent, drifts over time, ends
disconnected from its own early history.

## Root cause

`gateway/src/session/compaction.ts:115-124` (pre-fix):

```ts
const { error: sessErr } = await client
  .from("gateway_sessions")
  .update({
    compaction_summary: summary,          // bare UPDATE, not a merge
    compaction_at: new Date().toISOString(),
  })
  .eq("id", sessionID)
```

`compaction_summary` is a single `text` column. Each pass did a bare
UPDATE; the second pass clobbered the first pass's paragraph.

Worse, the summarizer on pass #2 was never given the prior summary as
input. `summarize()` received only the new head messages. The resulting
paragraph captured only what happened since the last compaction, not
the accumulated history.

A subtler secondary bug lived in the same path: `session.history()`
prepends the prior summary as a synthetic user message with a
freshly-minted UUID. On pass #2 that synthetic landed in `head` and
would be "re-summarized" — but then the subsequent
`UPDATE ... WHERE id IN (head_ids)` was a silent no-op for the
synthetic id (no matching row), so only real head rows got marked
compacted. Meanwhile the summarizer had already paraphrased a
paraphrase, losing fidelity on every iteration.

Mental model: "compaction is a rolling summary, so each pass summarizes
the latest chunk." True at pass #1. At pass #N the "latest chunk"
excludes everything from passes #1 through #N-1 — which are now gone
from `gateway_messages` (compacted) AND gone from the summary column
(overwritten).

## Fix

- `summarize()` grows an optional `priorSummary?: string | null`.
  When non-empty, it's injected as a leading user message tagged
  `[PRIOR SUMMARY — preserve every fact below]`.
- System prompt gains explicit fact-preservation language: *"If a
  PRIOR SUMMARY is provided, treat its facts as authoritative and
  carry them forward. The new summary must be a SUPERSET of the prior
  summary, not a replacement."*
- `runCompaction` reads `compaction_summary` from the session row
  before summarizing and passes it as `priorSummary`. It also filters
  synthetic messages out of `history` before splitting, so the no-op
  UPDATE path and the paraphrase-of-paraphrase path are both gone.
- The column overwrite is now safe because the new value is a superset
  of the old one by construction.

See commit [bbb1474](../../commit/bbb1474) and tests at
`gateway/tests/session/summary.test.ts` — three cases covering marker
injection, closing-prompt variant selection, and whitespace handling.

## Why the tests didn't catch it

No test ran a second compaction pass. The session test suite was a
thin sanity check around message persistence; compaction was untested
end-to-end. A single-pass test would pass, because pass #1 correctly
produces a summary of the head. The bug only manifests on pass #2 or
later — a case no test exercised.

Compounding: the unit I'd need to test is the *accumulation* of facts
across multiple compactions, which requires an LLM. Stubbing the LLM
is possible (as the fix's regression test does), but nobody had written
such a harness before this bug was found.

## Class of bug — where else to watch

**"Overwriting a lossy-compressed store"** is the core pattern. Any
time a column or row is written as a summarization / paraphrase /
hash-with-collisions of its inputs, replacing it wholesale on each
update compounds loss. The only safe update is one that takes the
prior value as input.

Other places this shape could hide in the codebase:

- The planner's `agent_catalog` column in `gateway_sessions` is
  wholesale-overwritten on every turn ([`gateway_sessions`
  schema](../../gateway/migrations/001_init.sql)). External may omit an
  agent from the catalog on a subsequent turn — we silently drop it
  even though the session's history references its tool calls. Same
  shape: overwrite of a lossy-valid store. Tracked in
  [`known-issues.md`](../known-issues.md) under `agent-catalog-overwrite`.
- Any future "session summary" features on top of compaction (e.g.
  per-turn summaries, cross-session rollups) must preserve-on-merge,
  not overwrite.
- The `gateway_tasks.usage` JSON column aggregates polling counts and
  signature stats. Today it's only written once per task, but if
  anything ever updates it in place, the same pattern applies.

Rule of thumb: **before writing to a column that replaces a previous
value, ask: is this column a pure projection of its source data (safe
to overwrite) or a lossy compression (must merge)?** If lossy, the
update must read-then-write, not write-only.
