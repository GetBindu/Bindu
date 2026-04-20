# bugs/

Two artifacts, one folder:

- [**`known-issues.md`**](./known-issues.md) — user-facing list of
  CURRENT limitations and known gotchas. Opens with a scannable table
  per subsystem; high-severity entries include a **Scenario** block so
  you can recognize the bug from the outside before diving into the
  code. Grows and shrinks over time — entries are REMOVED as the
  underlying issues get fixed.

- **Dated postmortems** — fixed bugs worth learning from, one file
  per bug, retained indefinitely. Organized by subsystem:
  - [`core/`](./core/) — Bindu Core (Python): `bindu/`, `alembic/`,
    `scripts/`
  - [`gateway/`](./gateway/) — gateway: `gateway/`
  - [`sdk/`](./sdk/) — SDKs: `sdks/`
  - [`frontend/`](./frontend/) — frontend: `frontend/`

Together they answer two different questions:

- *"What should I know before using this system today?"* → [`known-issues.md`](./known-issues.md)
- *"What has broken before, and what did it teach us?"* → dated postmortems in the subsystem folders

Neither is a replacement for GitHub Issues. Every bug still gets an
issue for triage and status; this folder is a durable, versioned record
— the kind of artifact a new maintainer can read six months in to
understand the codebase's failure modes.

## Folder layout

```
bugs/
├── README.md               (this file)
├── known-issues.md         (current unfixed issues, per-subsystem tables)
├── core/                   (Bindu Core postmortems)
│   └── 2026-04-18-*.md
├── gateway/                (gateway postmortems)
│   └── 2026-04-18-*.md
├── sdk/                    (SDK postmortems — none yet)
└── frontend/               (frontend postmortems — none yet)
```

## When to write a postmortem

Write one when the bug is **any** of:

- Security-relevant (auth, crypto, tenancy isolation, secret handling)
- Data loss or silent data corruption
- A correctness bug that shipped to users (production regression)
- A pattern-y bug where the same shape could exist in other code paths
- A concurrency or resource-leak bug (even if symptoms are subtle)

**Don't** write one for: typos, dependency bumps, style cleanups, pure
refactors, docs-only changes, or one-off bugs with no generalizable
lesson (e.g. "forgot a null check in a prototype").

The bar: if the fix teaches a future reader something about this
codebase's failure modes, it belongs here.

## Template

Copy this into a new file. Frontmatter fields in the first block are
required. The three sections under "Required" are required. The two
under "Strongly encouraged" are not enforced but are the reason this
folder exists — skipping them makes the postmortem a log entry rather
than a learning artifact.

```markdown
---
id: YYYY-MM-DD-short-kebab-slug
title: One-sentence description of the bug
severity: critical          # critical | high | medium | low
status: fixed               # fixed | mitigated | wont-fix
found: YYYY-MM-DD
fixed: YYYY-MM-DD
area: gateway/api           # free-form — e.g. gateway/api, bindu/core, sdks/typescript
commit: abc1234             # primary fix commit
pr:                         # optional — PR URL if one exists
issue:                      # optional — GitHub issue URL if one exists
---

## Symptom
What a user, operator, or downstream system observes when this bug
triggers. Start from the outside-in — not the code, the behavior.

## Root cause
The specific code path and WHY it was wrong. Include the file and line
reference from the pre-fix state (e.g. `gateway/src/api/plan-route.ts:155`).
Explain the mental model that led to the bug, not just the broken line.

## Fix
What changed, linking to the commit and the regression test. Short —
the commit message already carries the detail.

## Why the tests didn't catch it
Strongly encouraged. The single most useful section in the whole file.
Be honest: missing test, test ran single-threaded, triggering state
required production load, etc. "Nobody thought to test it" is a valid
answer — write it down.

## Class of bug — where else to watch
Strongly encouraged. Generalize the pattern beyond this one instance.
This is what turns a postmortem into a tool that prevents the next
bug instead of just recording the last one. Name specific other code
paths where the same shape could hide.
```

## File naming

`bugs/<subsystem>/YYYY-MM-DD-short-kebab-slug.md`. The date is the day
the bug was found (not necessarily fixed). The slug is 3–6 lowercase
words, kebab-case, describing the symptom. The subsystem folder
routes the file to the right audience (core maintainers, gateway
maintainers, etc.).

Examples:
- `bugs/gateway/2026-04-18-sse-cross-contamination.md`
- `bugs/core/2026-04-18-did-signature-fail-open.md`
- `bugs/sdk/2026-03-15-did-key-rotation-cache-stale.md`

## Writing `known-issues.md` entries

The file is structured per-subsystem. Each subsystem has:

1. A **Quick index** table — slug / severity / one-liner. Lets
   readers scan the whole surface in one screen.
2. Severity sections (High / Medium / Low / Nits) with detail
   entries underneath.

Style by severity:

- **High** entries use a **Scenario** blockquote at the top — a
  two-or-three-sentence story showing how the bug looks from
  outside (what a user does, what they expect, what they get). This
  is the "story format" that makes hard-to-diagnose bugs
  recognizable before you open a stack trace. Then a short
  *What's wrong* paragraph for the technical cause, a *Workaround*,
  and a *Tracking* line.
- **Medium / Low / Nits** keep the terse schema: Summary /
  Workaround / Tracking. These are easy enough to understand from
  a single paragraph and don't need a narrative.

When you fix an issue: remove its entry from `known-issues.md` and
(if it taught something) add a dated postmortem in the matching
subsystem folder. Reference the new postmortem from the
`Last updated` line so readers can find it.

## Deletion policy

Nothing gets deleted. A `status: fixed` postmortem stays in this folder
indefinitely. If a bug recurs, write a new postmortem and link to the
prior one from its "Class of bug" section — the pair tells a story the
single entry couldn't.

## Relationship to other tracking

- **GitHub Issues** — where bugs get filed, triaged, assigned, and
  closed. The issue tracker is the source of truth for **status**;
  this folder is the source of truth for **lessons**.

- **[`known-issues.md`](./known-issues.md)** — lives alongside the
  postmortems in this folder. User-facing list of CURRENT limitations
  and known gotchas. Entries are REMOVED as issues are fixed; a
  limitation that graduates into a fully-investigated postmortem moves
  out of `known-issues.md` and (if it taught us something) into a
  dated `YYYY-MM-DD-*.md` file in this folder.

- **Commit messages** — carry the tactical detail of the fix. The
  postmortem summarizes and generalizes; the commit message is the
  change diff's explanation.

## Adding a pre-commit or CI check

Intentionally not enforced today. If the template decays, add a check
in `.github/workflows/` that validates frontmatter schema and presence
of the required sections. Don't enforce prose quality — that makes
people skip writing postmortems entirely.
