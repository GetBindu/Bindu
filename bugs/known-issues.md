# Known Issues

_Last updated: 2026-04-20 — recipes/SSE/DID work on branch `feat/gateway-recipes` added 15 gateway entries (5 medium, 6 low, 5 nit) and narrowed two existing ones (`tool-name-collisions-silent` → `parse-agent-from-tool-greedy-mismatch`, `signature-verification-ok-when-unsigned` → `signature-verification-non-text-parts-unverified`) to the residual sub-bugs after partial resolutions landed. `did-document-endpoint-returns-raw-dict` removed — see [`core/2026-04-19-did-document-endpoint-raw-dict.md`](./core/2026-04-19-did-document-endpoint-raw-dict.md)._

This file is user-facing. It's the first thing a new contributor or
operator reads to calibrate expectations: what Bindu doesn't do
today, and what behaves in surprising ways. Every entry has a
workaround where one exists.

## How to read this file

1. **Scan the tables first.** Each subsystem (Gateway, Bindu Core,
   SDKs, Frontend) starts with a one-line-per-issue table — slug,
   severity, short description. That's enough to decide whether an
   issue matters to your deployment.
2. **Read the story when it bites you.** High-severity entries
   have a *Scenario* block telling you what the bug looks like
   from the outside. Start there when you suspect you're hitting
   one of these.
3. **Medium / low / nit entries** stay terse — Summary /
   Workaround / Tracking — because they're either easy to
   understand or easy to work around.

Entries are **REMOVED** from this file as issues are fixed. If the
fix teaches a generalizable lesson, a dated postmortem lands in the
matching `bugs/<subsystem>/` folder:

- [`bugs/gateway/`](./gateway/) — gateway postmortems
- [`bugs/core/`](./core/) — Bindu Core (Python) postmortems
- [`bugs/sdk/`](./sdk/) — SDK postmortems (none yet)
- [`bugs/frontend/`](./frontend/) — frontend postmortems (none yet)

See [`bugs/README.md`](./README.md) for the postmortem template.

Reporting: if you hit one of these and want to help, open a GitHub
Issue referencing the slug (e.g. "Fixes `context-window-hardcoded`").

---

## Table of contents

| Subsystem | High | Medium | Low | Nit |
|---|---:|---:|---:|---:|
| [Gateway](#gateway) | 3 | 15 | 19 | 9 |
| [Bindu Core (Python)](#bindu-core-python) | 4 | 7 | 2 | 0 |
| [SDKs (TypeScript)](#sdks-typescript) | — | — | — | — |
| [Frontend](#frontend) | — | — | — | — |

---

## Gateway

### Quick index

| Slug | Severity | One-line |
|---|---|---|
| [`context-window-hardcoded`](#context-window-hardcoded) | high | Compaction threshold assumes a 200k-token context window |
| [`poll-budget-unbounded-wall-clock`](#poll-budget-unbounded-wall-clock) | high | `sendAndPoll` can stall 5 minutes per tool call |
| [`no-session-concurrency-guard`](#no-session-concurrency-guard) | high | Two `/plan` calls on the same session tangle their histories |
| [`abort-signal-not-propagated-to-bindu-client`](#abort-signal-not-propagated-to-bindu-client) | medium | Client disconnect doesn't cancel in-flight peer polls |
| [`permission-rules-not-enforced-for-tool-calls`](#permission-rules-not-enforced-for-tool-calls) | medium | Permission service exists but is never called for tool calls |
| [`parse-agent-from-tool-greedy-mismatch`](#parse-agent-from-tool-greedy-mismatch) | medium | SSE `agent` field wrong when agent names contain underscores |
| [`agent-catalog-overwrite`](#agent-catalog-overwrite) | medium | Each `/plan` wholesale-overwrites the session's agent catalog |
| [`signature-verification-non-text-parts-unverified`](#signature-verification-non-text-parts-unverified) | medium (sec) | `DataPart` / `FilePart` bypass signature verification |
| [`pinned-did-no-format-validation`](#pinned-did-no-format-validation) | medium | Any string is accepted as `pinnedDID`; no DID shape check |
| [`recipe-permission-ask-treated-as-allow`](#recipe-permission-ask-treated-as-allow) | medium | `permission: recipe: { "x": "ask" }` silently allows |
| [`ctx-ask-not-wired-for-recipes`](#ctx-ask-not-wired-for-recipes) | medium | Recipe permission hook is a no-op at runtime |
| [`supabase-error-surfaces-as-generic-sse-error`](#supabase-error-surfaces-as-generic-sse-error) | medium | Mid-stream DB failures emit untyped `event: error` |
| [`did-resolver-no-key-id-selection`](#did-resolver-no-key-id-selection) | medium (sec) | Resolver picks the first public key; breaks during rotation |
| [`list-messages-pagination-silent`](#list-messages-pagination-silent) | medium | Sessions >1000 messages silently truncate oldest |
| [`tool-input-sent-as-textpart`](#tool-input-sent-as-textpart) | medium | Skills expecting `DataPart` receive `TextPart` with stringified JSON |
| [`no-rate-limit-cors-body-size-limit`](#no-rate-limit-cors-body-size-limit) | medium | No rate limit / CORS / body-size limit on the Hono app |
| [`prompt-injection-scrubbing-theater`](#prompt-injection-scrubbing-theater) | medium (sec) | The regex scrubber offers false confidence |
| [`no-graceful-shutdown`](#no-graceful-shutdown) | medium | In-flight `/plan` streams drop mid-frame on close |
| [`assistant-message-lost-on-stream-error`](#assistant-message-lost-on-stream-error) | medium | Mid-stream errors lose completed tool calls from history |
| [`json-schema-to-zod-incomplete`](#json-schema-to-zod-incomplete) | medium | Converter ignores `enum` / `oneOf` / pattern / etc. |
| [`compaction-dedupe-single-process-only`](#compaction-dedupe-single-process-only) | low | Dedupe is in-process; horizontal scaling would race |
| [`no-ttl-cleanup`](#no-ttl-cleanup) | low | `session.ttlDays` configured but no cleanup job runs |
| [`token-estimation-chars-div-4`](#token-estimation-chars-div-4) | low | `chars/4` wrong for code and CJK |
| [`did-resolver-no-stampede-protection`](#did-resolver-no-stampede-protection) | low | Simultaneous cache-miss fetches for the same DID |
| [`bearer-env-error-collapses-to-transport`](#bearer-env-error-collapses-to-transport) | low | Missing env var surfaces as a generic transport error |
| [`resume-race-duplicate-session`](#resume-race-duplicate-session) | low | Concurrent first-time `/plan` for a session throws 500 on second |
| [`cancel-casing-not-retried`](#cancel-casing-not-retried) | low | `tasks/cancel` sends only camelCase; leaks tasks on snake-case peers |
| [`health-endpoint-no-dependency-probe`](#health-endpoint-no-dependency-probe) | low | `GET /health` doesn't probe dependencies |
| [`no-request-id-in-logs`](#no-request-id-in-logs) | low | No correlation ID for `/plan` requests |
| [`no-config-hot-reload`](#no-config-hot-reload) | low | Config changes need a full restart |
| [`resolve-env-limited-to-simple-var`](#resolve-env-limited-to-simple-var) | low | Env interpolation only matches bare `$VAR` |
| [`compaction-summary-injected-as-user-role`](#compaction-summary-injected-as-user-role) | low | Summary injected as `role: "user"` — could confuse the LLM |
| [`revert-millisecond-ties-nondeterministic`](#revert-millisecond-ties-nondeterministic) | low | Millisecond-tied `created_at` ordering is non-deterministic |
| [`revert-doesnt-cancel-remote-tasks`](#revert-doesnt-cancel-remote-tasks) | low | `revertTo` doesn't cancel still-running peer tasks |
| [`empty-agents-catalog-no-400`](#empty-agents-catalog-no-400) | low | `/plan` with empty `agents[]` runs and returns an LLM error |
| [`no-migration-rollback`](#no-migration-rollback) | low | Migrations forward-only — no paired `down.sql` |
| [`recipe-no-hot-reload`](#recipe-no-hot-reload) | low | Recipe changes require a gateway restart |
| [`load-recipe-sse-frames-ambiguous`](#load-recipe-sse-frames-ambiguous) | low | `load_recipe` and peer calls use the same SSE `agent` field |
| [`recipe-file-enumeration-no-truncation-signal`](#recipe-file-enumeration-no-truncation-signal) | low | 10+ files per recipe silently truncated in tool output |
| [`faq-agent-did-name-mismatch`](#faq-agent-did-name-mismatch) | low | Fleet's `faq_agent.py` registers as `bindu_docs_agent` |
| [`fleet-env-can-desync-after-seed-rotation`](#fleet-env-can-desync-after-seed-rotation) | low | Stale `$*_DID` env vars survive agent seed rotation |
| [`provider-openrouter-hardcoded`](#provider-openrouter-hardcoded) | low | `model` field assumes OpenRouter prefix |
| [`tasks-recorded-is-dead-state`](#tasks-recorded-is-dead-state) | nit | Unused `tasksRecorded` field in the planner |
| [`map-finish-reason-pointless-ternary`](#map-finish-reason-pointless-ternary) | nit | Conditional type that evaluates to `any` either way |
| [`db-effect-promise-swallows-errors`](#db-effect-promise-swallows-errors) | nit | `Effect.promise` silently swallows rejected promises |
| [`test-coverage-gaps`](#test-coverage-gaps) | nit | Backlog list of missing test scenarios |
| [`accept-header-not-enforced-on-plan`](#accept-header-not-enforced-on-plan) | nit | `Accept: text/event-stream` not required |
| [`openapi-sse-schemas-unused`](#openapi-sse-schemas-unused) | nit | 13 redocly `no-unused-components` warnings on SSE schemas |
| [`no-planner-integration-test`](#no-planner-integration-test) | nit | Request → SSE end-to-end test missing |
| [`no-health-handler-integration-test`](#no-health-handler-integration-test) | nit | `/health` only has pure-helper unit tests |
| [`story-chapter5-missing-oauth-scope-explanation`](#story-chapter5-missing-oauth-scope-explanation) | nit | DID chapter assumes reader knows OAuth scopes |

### High

### context-window-hardcoded

**Severity:** high

> **Scenario.** You switch the gateway to GPT-4o-mini (128k context).
> After a few long turns, the next planner request sends >128k
> tokens to the provider and gets back a `context_length_exceeded`
> 400. You check the logs expecting to see compaction kick in.
> It didn't. The threshold is hardwired to 200k.

**What's wrong.** The compaction threshold in
[`gateway/src/session/overflow.ts`](../gateway/src/session/overflow.ts)
assumes a 200,000-token context window (Claude Opus 4.x). Smaller
models (GPT-4o-mini 128k, Haiku 200k) or much larger ones (Gemini
Flash 1M) make compaction fire at the wrong time — either too late
(provider rejects for overflow before compaction runs) or too
early (unnecessary summarization cost).

**Workaround:** Pass an explicit `threshold.contextWindow`
matching your actual model when calling `compactIfNeeded`. For
multi-model deployments this needs per-model configuration the
gateway doesn't currently expose.

**Status:** ✅ **Fixed.** `thresholdForModel()` in
[`gateway/src/session/overflow.ts`](../gateway/src/session/overflow.ts)
now resolves the context window from a lookup table keyed on
`provider/modelId` (Anthropic 4.x = 200k, GPT-4o/4o-mini = 128k,
GPT-4.1 = ~1M, o3 = 200k). Unknown models fall back to 128k
(conservative — triggers compaction earlier rather than letting
the caller hit `context_length_exceeded`). Operators can still
pass an explicit override via `compactIfNeeded({threshold})` for
exotic models. Threshold wiring goes through
`compaction.ts:compactIfNeeded` which now takes the planner's
actual model into account. Guarded by
[`gateway/tests/session/overflow-threshold.test.ts`](../gateway/tests/session/overflow-threshold.test.ts)
(14 tests).

**Tracking:** _(no issue yet)_

### poll-budget-unbounded-wall-clock

**Severity:** high

> **Scenario.** A `/plan` request makes one tool call to a Bindu
> peer. The peer is stuck in `working` state and never advances.
> `sendAndPoll` retries 60 times with exponential backoff —
> **five minutes worst case, per tool call.** Meanwhile the SSE
> stream to the user stays open, the session row stays locked,
> and the user's browser eventually gives up. The peer poll keeps
> running.

**What's wrong.** `sendAndPoll` in
[`gateway/src/bindu/client/poll.ts`](../gateway/src/bindu/client/poll.ts)
defaults to 60 polls × backoff up to 10 s. There's no
overall `/plan` deadline, only a per-HTTP timeout on the
individual JSON-RPC round trip. A single hung peer can stall an
entire plan indefinitely.

**Workaround:** Pass an explicit `maxPolls` or shorter
`backoffMs` schedule when instantiating the Bindu client. Client
disconnects don't help — see
`abort-signal-not-propagated-to-bindu-client` below. For
request-level deadlines the caller must enforce them externally
(e.g. client-side timeout on the SSE `fetch`).

**Tracking:** _(no issue yet)_

### no-session-concurrency-guard

**Severity:** high

> **Scenario.** Alice has two browser tabs on the same session.
> Tab 1 sends `/plan`. Before it finishes, tab 2 sends another
> `/plan` for the same session. Both planners append to
> `gateway_messages` concurrently. The second LLM call sees the
> first call's half-written `tool_use` without its paired
> `tool_result` — the assistant message sequence is now broken.
> LLM hallucinates or errors. Worse: the session's history is now
> permanently in an inconsistent state on disk.

**What's wrong.** Two `/plan` requests sharing the same
`session_id` both append to `gateway_messages` with no
serialization. Their histories interleave and the LLM's
`tool_use` / `tool_result` pairing silently tangles across
sessions. The compaction dedupe fix ([commit 0655ac1](../commit/0655ac1))
prevents *compaction* races but does not serialize plan turns
themselves.

**Workaround:** Clients should not run concurrent `/plan`
requests against the same session. For genuine concurrent use
(multiple tabs, etc.), use distinct session IDs and reconcile
externally.

**Tracking:** _(no issue yet)_

### Medium

### abort-signal-not-propagated-to-bindu-client

**Severity:** medium
**Summary:** When a client disconnects mid-`/plan`, the gateway's
SSE handler aborts — but in-flight polling loops against downstream
Bindu agents ([`gateway/src/bindu/client/poll.ts`](../gateway/src/bindu/client/poll.ts))
do not cancel. Each in-flight tool call continues for up to 60
attempts × backoff (≈ 5 minutes worst case) after the user is gone.
**Workaround:** None client-side. Accept that aborted `/plan`
requests may leave stragglers consuming gateway + peer compute for
several minutes.
**Tracking:** _(no issue yet)_ (related to `poll-budget-unbounded-wall-clock`)

### permission-rules-not-enforced-for-tool-calls

**Severity:** medium
**Summary:** `agents/planner.md` declares `permission: agent_call:
ask`, and the Permission service exists and evaluates wildcards
correctly. But the planner's tool-execution path
([`gateway/src/session/prompt.ts`](../gateway/src/session/prompt.ts))
never calls `Permission.Service.evaluate()` before running a Bindu
tool. The permission system is effectively dead code for tool calls
today.
**Workaround:** Control tool access via the `agents[]` catalog the
caller sends in the `/plan` request — only include agents the caller
is allowed to invoke.
**Tracking:** _(no issue yet)_

### parse-agent-from-tool-greedy-mismatch

**Severity:** medium
**Summary:** The collision half of this bug is now
**rejected** at plan-open time — `findDuplicateToolIds` in
[`gateway/src/planner/index.ts`](../gateway/src/planner/index.ts)
returns a 400 when two `(agent, skill)` pairs normalize to the
same tool id. What remains: `parseAgentFromTool` in
[`gateway/src/api/plan-route.ts`](../gateway/src/api/plan-route.ts)
uses a non-greedy regex `^call_(.+?)_(.+)$`, so an agent whose
name contains an underscore (e.g. `research_v2`) emits SSE
`task.started` events with `agent=research`, `skill=v2_x` instead
of the intended `agent=research_v2`, `skill=x`.
**Workaround:** Avoid underscores in agent names in the catalog
you send on `/plan`. If you must, rely on `agent_did` / `task_id`
for correlation, not the SSE `agent` field.
**Tracking:** _(no issue yet)_

### agent-catalog-overwrite

**Severity:** medium
**Summary:** `db.updateSessionCatalog` wholesale-overwrites
`gateway_sessions.agent_catalog` on every `/plan`. If the caller
omits an agent from a subsequent turn's catalog (e.g. temporary
unreachability, inventory churn), the gateway drops it from the
session's recorded catalog even though the session's history
references its prior tool calls. Also exposed to a concurrency race
(see [`2026-04-18-compaction-concurrent-races.md`](./gateway/2026-04-18-compaction-concurrent-races.md)
— same shape, different column).
**Workaround:** Always send the full agent catalog on every turn,
even if individual agents are temporarily unavailable.
**Tracking:** _(no issue yet)_

### signature-verification-non-text-parts-unverified

**Severity:** medium (security-adjacent)
**Summary:** The envelope-ambiguity half of this bug is **fixed**
— `<remote_content verified="...">` is now four-valued
(`yes | no | unsigned | unknown`), so the planner LLM can tell a
real cryptographic pass from "nothing was signed". What remains:
`verifyArtifact` in
[`gateway/src/bindu/identity/verify.ts`](../gateway/src/bindu/identity/verify.ts)
only inspects text parts. `file` and `data` parts are never
verified, so a peer moving payload into a `DataPart` bypasses
signature checks entirely even when `verifyDID: true` is set.
**Workaround:** Refuse peers that return `data` or `file` parts
for responses that must be verified. The gateway does not enforce
this constraint today.
**Tracking:** _(no issue yet)_

### did-resolver-no-key-id-selection

**Severity:** medium (security-adjacent)
**Summary:** `primaryPublicKeyBase58` in
[`gateway/src/bindu/identity/resolve.ts`](../gateway/src/bindu/identity/resolve.ts)
picks the FIRST public key found in a peer's DID Document. If the
peer publishes multiple keys — e.g. during a rotation window listing
both old and new — the wrong key may be selected for verification,
causing valid signatures to fail or the wrong key to be used
altogether. The A2A DID spec allows explicit `keyId` selection in
signature metadata; the gateway does not consult it.
**Workaround:** For peers using DID verification, pin them to a
specific DID via `trust.pinnedDID` and coordinate rotation windows
out-of-band.
**Tracking:** _(no issue yet)_

### list-messages-pagination-silent

**Severity:** medium
**Summary:** `db.listMessages` has a default limit of 1000 rows
([`gateway/src/db/index.ts`](../gateway/src/db/index.ts)). Very long
sessions silently truncate to the most recent 1000 messages, skipping
the oldest. The planner loads this into its history; the LLM sees a
partial session that starts mid-stream. No error, no warning.
Compaction can fire and accurately summarize what it sees, but the
oldest messages were never in scope.
**Workaround:** Trigger compaction early on sessions expected to
grow large. Long-term, paginate via `created_at` cursor.
**Tracking:** _(no issue yet)_

### tool-input-sent-as-textpart

**Severity:** medium
**Summary:** The planner's tool-execution path
([`gateway/src/planner/index.ts`](../gateway/src/planner/index.ts))
serializes arguments with `JSON.stringify(args)` and sends them as a
Bindu `TextPart`. Many deployed skills expect a structured
`DataPart` (`{kind:"data", data:{…}}`) — especially skills whose
server-side validator parses a typed input schema. Skills that only
accept `DataPart` reject the `TextPart` outright; skills that try to
parse the JSON string out of a text field behave unpredictably.
**Workaround:** None client-side — the gateway always sends
`TextPart`. Affected skills must accept either form on their server
side until this is fixed.
**Tracking:** _(no issue yet)_

### no-rate-limit-cors-body-size-limit

**Severity:** medium
**Summary:** The Hono app
([`gateway/src/server/index.ts`](../gateway/src/server/index.ts))
has no rate limit, no CORS policy, and no body-size limit. A single
client can submit large `/plan` requests or fire many concurrent
requests without any throttling; browser clients from different
origins have no explicit policy. The absence of a body-size limit is
a trivial DoS vector — a 500 MB JSON payload is accepted, parsed,
and held in memory.
**Workaround:** Deploy behind a reverse proxy (nginx, Cloudflare,
API Gateway) that provides these controls. The gateway assumes it
runs behind such a proxy today.
**Tracking:** _(no issue yet)_

### prompt-injection-scrubbing-theater

**Severity:** medium (security)
**Summary:** `wrapRemoteContent` in
[`gateway/src/planner/index.ts`](../gateway/src/planner/index.ts)
strips literal strings like `"ignore previous"` and
`"disregard earlier"` from peer responses before handing them to the
planner LLM. This is trivially bypassable with capitalization,
Unicode homoglyphs, paraphrasing, JSON-encoding the instruction, or
placing it in a non-text part (`file`, `data` — which aren't
scrubbed at all). It offers a false sense of safety without actually
blocking prompt injection; the current defense is worse than no
defense because downstream code may assume it's doing something.
**Workaround:** Do not rely on the scrubber for prompt-injection
resistance. For untrusted peers, apply one or more of: (a) isolate
peer output into an LLM sub-call with its own restricted system
prompt that produces structured data, not free-form instructions;
(b) use provider-side structured-output / tool-choice constraints to
prevent the planner from obeying arbitrary peer instructions;
(c) cap peer responses to a strict JSON schema server-side.
**Tracking:** _(no issue yet)_

### no-graceful-shutdown

**Severity:** medium
**Summary:** The gateway's `close()` function
([`gateway/src/index.ts`](../gateway/src/index.ts)) calls
`httpServer.close()` and `runtime.dispose()` back-to-back. In-flight
`/plan` streams are dropped mid-frame — clients see a truncated
SSE, and the assistant message may be partially written but not
committed. No draining, no deadline, no 5xx return for requests in
flight during a rolling restart.
**Workaround:** Rely on the reverse proxy to drain connections
before sending SIGTERM to the gateway, and run at least two gateway
replicas so dropped connections can be retried against the other.
**Tracking:** _(no issue yet)_

### assistant-message-lost-on-stream-error

**Severity:** medium (data loss, billing)
**Summary:** If the LLM stream errors mid-turn
([`gateway/src/session/prompt.ts`](../gateway/src/session/prompt.ts)),
the Effect generator fails immediately. Tool calls that already
completed (and were already billed via the Bindu agent) are lost
from the assistant message — they never get persisted to
`gateway_messages`. The audit row in `gateway_tasks` still exists
(the tool call completed from the gateway's perspective), but the
session-level history shows no record of the tool_use, so replay is
inconsistent with the audit log.
**Workaround:** None at the application level. Operators should
correlate `gateway_tasks` with `gateway_messages` when investigating
session gaps — don't trust the assistant-message view alone.
**Tracking:** _(no issue yet)_

### json-schema-to-zod-incomplete

**Severity:** medium
**Summary:** `jsonSchemaToZod` in
[`gateway/src/planner/index.ts`](../gateway/src/planner/index.ts)
converts an inbound skill's `inputSchema` to a Zod validator for the
planner LLM. It handles `type: string|number|integer|boolean|array|
object` but ignores every other keyword: `enum`, `oneOf`, `anyOf`,
`pattern`, `minLength`/`maxLength`, `minimum`/`maximum`,
`additionalProperties`, `format`, and more. The planner LLM therefore
receives no signal about valid values; invalid input passes local
validation and reaches the peer, failing late with a JSON-RPC error.
**Workaround:** Skills should document their full input constraints
in their human-readable `description` so the planner LLM picks them
up from the prompt rather than the schema.
**Tracking:** _(no issue yet)_

### Low

### compaction-dedupe-single-process-only

**Severity:** low (correct today, architectural ceiling)
**Summary:** The fix for concurrent compaction races
([commit 0655ac1](../commit/0655ac1) /
[`2026-04-18-compaction-concurrent-races.md`](./gateway/2026-04-18-compaction-concurrent-races.md))
uses an in-process `Map<SessionID, Promise>`. A horizontally-scaled
deployment of the gateway (multiple Node processes fronting one
Supabase) could still race across processes. Single-process Phase 1
is correct.
**Workaround:** Run a single gateway process. Horizontal scaling is
a Phase 2 concern — when it lands, add a Postgres version column on
`gateway_sessions` with optimistic-concurrency semantics in the
compaction UPDATE, or wrap the whole compaction in a stored
procedure.
**Tracking:** _(no issue yet)_

### no-ttl-cleanup

**Severity:** low
**Summary:** Config declares `gateway.session.ttlDays` (default 30)
but nothing actually cleans up old sessions. `gateway_sessions`,
`gateway_messages`, and `gateway_tasks` grow unbounded.
**Workaround:** Run a scheduled Supabase SQL job to delete rows
older than your desired TTL. The gateway does not do this
automatically.
**Tracking:** _(no issue yet)_

### token-estimation-chars-div-4

**Severity:** low
**Summary:** `approxTokens` in
[`gateway/src/session/overflow.ts`](../gateway/src/session/overflow.ts)
uses `chars / 4` as its token count heuristic. Accurate for English
prose; wrong for code (more tokens per char due to punctuation),
wildly wrong for CJK (closer to `chars / 1.5`). Combined with
`context-window-hardcoded`, compaction timing for non-English
sessions is unreliable.
**Workaround:** Set a more conservative `triggerFraction` (e.g.
`0.6` instead of `0.8`) if your sessions are primarily code or
CJK-language content.
**Tracking:** _(no issue yet)_

### did-resolver-no-stampede-protection

**Severity:** low
**Summary:** The DID resolver in
[`gateway/src/bindu/identity/resolve.ts`](../gateway/src/bindu/identity/resolve.ts)
caches DID Documents with a 5-minute TTL. When the cache expires (or
is cold on first call), concurrent `resolve()` calls for the same
DID all miss and issue simultaneous HTTP fetches to the peer's
`/did/resolve`. Functionally harmless; wasteful.
**Workaround:** None needed in practice — 5 minutes is long enough
that stampedes are rare. If they become a problem, add a
second-level in-flight dedupe (same pattern as compaction-dedupe).
**Tracking:** _(no issue yet)_

### bearer-env-error-collapses-to-transport

**Severity:** low
**Summary:** When `auth: { type: "bearer_env", envVar: "FOO" }` is
configured for a peer but `$FOO` is unset, `authHeaders()` throws
from inside the async `runCall` in the Bindu client. The error is
caught by the Effect machinery and wrapped as a generic transport
error (`BinduError.transport(...)`), losing the "configuration
missing" context. The operator can't tell "missing env" from "peer
down."
**Workaround:** Validate required env vars at gateway boot. Or tail
the logs for `"auth: env var … is not set"` — the message is still
present in the error string, just buried under `"transport:"`.
**Tracking:** _(no issue yet)_

### resume-race-duplicate-session

**Severity:** low
**Summary:** Two concurrent `/plan` requests with the same
`session_id` where neither yet exists in `gateway_sessions` will
both miss the `getSession` lookup and both call `sessions.create()`,
producing two rows with the same `external_session_id`. The `UNIQUE`
constraint on `external_session_id` will cause the second insert to
fail — the second request errors back to the caller with a 500.
**Workaround:** Retry the failing request. The first insert
succeeded, so a retry resolves to the existing row.
**Tracking:** _(no issue yet)_

### cancel-casing-not-retried

**Severity:** low
**Summary:** When `sendAndPoll` exhausts its poll budget
([`gateway/src/bindu/client/poll.ts`](../gateway/src/bindu/client/poll.ts)),
it issues a best-effort `tasks/cancel` to the peer. That cancel
sends `taskId` in camelCase only — it never does the snake_case
retry flip that the poll loop itself performs. For peers that
require `task_id` in snake_case (the very case the flip exists for),
the cancel silently fails and the remote task leaks.
**Workaround:** None. Peers that require snake-case params for
`tasks/cancel` need to support camelCase too, or the task will
orphan on poll timeout.
**Tracking:** _(no issue yet)_

### health-endpoint-no-dependency-probe

**Severity:** low
**Summary:** `GET /health`
([`gateway/src/server/index.ts`](../gateway/src/server/index.ts))
returns `200 {ok: true}` regardless of whether Supabase is reachable
or the configured LLM provider is accepting requests. Load balancers
see "healthy" while the gateway is unable to serve `/plan` traffic.
Good for liveness, useless for readiness.
**Workaround:** Add a separate readiness check in your deployment
that hits `/plan` with a no-op payload and a short deadline.
**Tracking:** _(no issue yet)_

### no-request-id-in-logs

**Severity:** low
**Summary:** `/plan` handler produces no request ID, correlation
ID, or tracing context. When an SSE stream errors and the client
reports a problem, there's no way to correlate the client's
observation with a server-side log line. Server-side logs don't
include session ID either for most events.
**Workaround:** Set `X-Request-Id` on the reverse proxy and include
it in proxy access logs; correlate by timestamp and peer URL.
**Tracking:** _(no issue yet)_

### no-config-hot-reload

**Severity:** low
**Summary:** Changes to `agents/planner.md`, `gateway.config.json`,
or any permission rules require a full gateway restart. The config
loader reads files once at boot via
[`gateway/src/config/loader.ts`](../gateway/src/config/loader.ts).
**Workaround:** Restart the gateway. For live-tuning the planner
prompt, consider reading it dynamically from DB or a separate
mutable source.
**Tracking:** _(no issue yet)_

### resolve-env-limited-to-simple-var

**Severity:** low
**Summary:** `resolveEnv` in
[`gateway/src/config/loader.ts`](../gateway/src/config/loader.ts)
only matches bare `"$VAR"` strings. It does not handle
`"${VAR}/suffix"`, default values (`"${VAR:-default}"`), nested
interpolation, or shell-style expansion. A config value like
`"https://${HOST}/api"` passes through as a literal string.
**Workaround:** Precompute interpolated values in your env or
config file; don't rely on shell-style expansion inside config
strings.
**Tracking:** _(no issue yet)_

### compaction-summary-injected-as-user-role

**Severity:** low
**Summary:** The compaction summary is injected back into history
as a synthetic message with `role: "user"`
([`gateway/src/session/index.ts`](../gateway/src/session/index.ts)).
Works, but the LLM may mistake the summary for the current user
turn's message — especially when the summary starts with a phrase
the model could interpret as a directive. A system-role injection
(or explicit `[SYSTEM: prior context]` tagging) would be safer.
**Workaround:** The prefix `[Prior session context, compacted]`
already signals the nature of the content; in practice the planner
handles it correctly. Watch for cases where the model echoes the
summary verbatim as if it were a user question.
**Tracking:** _(no issue yet)_

### revert-millisecond-ties-nondeterministic

**Severity:** low
**Summary:** `revertTo` and `revertLastTurn` in
[`gateway/src/session/revert.ts`](../gateway/src/session/revert.ts)
use `created_at` as the boundary for "everything after this
message." If multiple messages were inserted within the same
millisecond (rare but possible under contention), their relative
order is non-deterministic — revert may include or exclude some of
them based on DB-internal ordering.
**Workaround:** Inspect the reverted row set after a revert;
manually unmark any mis-reverted rows. A Phase 2 fix would switch to
a monotonically-increasing `seq` column.
**Tracking:** _(no issue yet)_

### revert-doesnt-cancel-remote-tasks

**Severity:** low
**Summary:** `revertTo` marks local audit rows as `reverted=true`
but does NOT send `tasks/cancel` to the peers for any still-running
Bindu tasks in the reverted window. The remote tasks continue,
consuming peer resources and (for paid skills) accruing cost until
they finish on their own. This is documented as intentional in the
code — peers have already done the work, and cancel semantics are
complex — but may surprise operators.
**Workaround:** Accept that revert only clears local state.
Stragglers complete on the peer side and their audit rows stay
marked reverted so they're hidden from resume.
**Tracking:** _(no issue yet)_

### empty-agents-catalog-no-400

**Severity:** low
**Summary:** `PlanRequest.agents` has a default of `[]`, so a
`/plan` request with no agents is accepted. The planner runs with
zero tools, the LLM attempts to call a tool it has no access to,
and the response is an error message from the LLM — not a clear
"you forgot to send agents" 400.
**Workaround:** Always include at least one agent in the request,
or pre-validate the `agents.length` client-side.
**Tracking:** _(no issue yet)_

### no-migration-rollback

**Severity:** low
**Summary:** Migrations under `gateway/migrations/` are forward-only
— no paired `down.sql` for each change. Reverting a migration
requires manual SQL work.
**Workaround:** For a production deployment that may need rollback,
maintain rollback scripts outside the `migrations/` folder. This is
a common choice for small projects; fix only if the team actively
needs reversible migrations.
**Tracking:** _(no issue yet)_

### Nits

### tasks-recorded-is-dead-state

**Severity:** nit
**Summary:** `tasksRecorded: string[]` accumulated in the planner
([`gateway/src/planner/index.ts`](../gateway/src/planner/index.ts))
is populated inside `buildSkillTool` but never returned via SSE,
never persisted, and never read. Dead code.
**Workaround:** None needed. Remove in a cleanup pass.
**Tracking:** _(no issue yet)_

### map-finish-reason-pointless-ternary

**Severity:** nit
**Summary:** `mapFinishReason` in
[`gateway/src/session/prompt.ts`](../gateway/src/session/prompt.ts)
has a parameter type `StreamEvent["type"] extends "finish" ? any :
any` which is always `any`. The conditional type adds no
information.
**Workaround:** None needed. Simplify in a cleanup pass.
**Tracking:** _(no issue yet)_

### db-effect-promise-swallows-errors

**Severity:** nit (correctness-adjacent)
**Summary:** Two paths in
[`gateway/src/db/index.ts`](../gateway/src/db/index.ts) use
`Effect.promise(...)` which resolves even when the underlying
promise rejects (it treats rejection as a defect, not an Effect
error). Transient Supabase failures at those call sites may silently
resolve without being surfaced to the caller.
**Workaround:** None client-side. Audit `Effect.promise` call sites;
prefer `Effect.tryPromise` with an explicit `catch` for any
non-trivial operation.
**Tracking:** _(no issue yet)_

### test-coverage-gaps

**Severity:** nit
**Summary:** The test suite does not cover: concurrent `/plan`
requests end-to-end (only the pubsub filter is tested); compaction
correctness on long multi-pass sessions (only the wrapper dedupe and
summarizer prompt are tested); revert; SSE frame ordering under
load; non-English payloads; sessions larger than the 1000-row
pagination limit; missing `bearer_env` env vars; aborted requests
propagating to the Bindu client; the snake_case flip on
`tasks/cancel`.
**Workaround:** None — this is an internal backlog item.
Contributors tackling any of the fixable items above should add a
test for it in the same PR.
**Tracking:** _(no issue yet)_

<!-- ------------------------------------------------------------ -->
<!-- Added 2026-04-20 from recipes/SSE/DID session work            -->
<!-- ------------------------------------------------------------ -->

### pinned-did-no-format-validation

**Severity:** medium
**Summary:** `PeerAuthRequest.trust.pinnedDID` in
[`gateway/src/planner/index.ts`](../gateway/src/planner/index.ts)
is `z.string().optional()` with no shape check. A caller can send
`pinnedDID: "hello"` or accidentally an un-interpolated template
literal like `"${RESEARCH_DID}"`, and the gateway will echo that
string in every SSE `agent_did` frame and try (vainly) to resolve
it for signature verification. Observed in practice when a Postman
user copy-pasted a bash-style variable reference into the request
body.
**Workaround:** Validate DID shape client-side before sending. At
minimum ensure the string starts with `did:bindu:` or `did:key:`.
**Tracking:** _(no issue yet)_

### recipe-permission-ask-treated-as-allow

**Severity:** medium
**Summary:**
[`Recipe.available`](../gateway/src/recipe/index.ts) filters the
recipe list shown to an agent by excluding anything whose
`permission.recipe` resolves to `deny`. The evaluator is
three-valued (`allow | deny | ask`) — `ask` falls through and the
recipe is shown AND loadable. With the `ctx.ask` hook unwired (see
next entry), `"ask"` is silently identical to `"allow"`.
**Workaround:** Treat `"ask"` as if it were `"allow"` for recipes
today. If you need to restrict, use `"deny"`.
**Tracking:** _(no issue yet)_

### ctx-ask-not-wired-for-recipes

**Severity:** medium
**Summary:** [`tool/recipe.ts`](../gateway/src/tool/recipe.ts)
calls `ctx.ask({permission: "recipe", target: name})` before
loading a recipe body, guarded by `if (ctx.ask)`. The `ctx.ask`
field is marked optional in `ToolContext` and
[`wrapTool`](../gateway/src/session/prompt.ts) never sets it. So
the gate is a permanent no-op — recipes load unconditionally
regardless of agent permission config. This is a separate concern
from `permission-rules-not-enforced-for-tool-calls` which targets
the broader tool-call gate.
**Workaround:** Don't rely on `permission.recipe` in agent configs
for production access control. Wait for Phase-2 permission UI.
**Tracking:** _(no issue yet)_

### supabase-error-surfaces-as-generic-sse-error

**Severity:** medium
**Summary:**
[`plan-route.ts`](../gateway/src/api/plan-route.ts) wraps
`runPlan` in a catch that emits `event: error` with only
`{message: string}`. Callers can't programmatically distinguish a
Supabase outage from a peer crash from an LLM failure — all three
look identical on the wire. Operators debugging prod incidents
have to grep logs.
**Workaround:** Tail gateway logs out of band. Client-side, treat
any `event: error` as "retry with exponential backoff" regardless
of cause.
**Tracking:** _(no issue yet)_

### recipe-no-hot-reload

**Severity:** low
**Summary:**
[`Recipe.layer`](../gateway/src/recipe/index.ts) reads
`gateway/recipes/` once at boot. Adding, editing, or deleting a
recipe markdown file has no effect until the gateway process
restarts. Authoring loop is Ctrl-C + `npm run dev` per change.
**Workaround:** Script `npm run dev` to auto-restart on
`recipes/**/*.md` changes using `nodemon` or `tsx watch` with a
wider include. Or edit + restart; the recipe layer init is cheap.
**Tracking:** _(no issue yet)_

### load-recipe-sse-frames-ambiguous

**Severity:** low
**Summary:** When the planner calls the internal `load_recipe`
tool, the SSE stream emits `task.started` / `task.artifact` /
`task.finished` frames with `agent: "load_recipe"` and
`agent_did: null`. Consumers parsing `task.*` frames by peer
correlation have no crisp way to tell this apart from a peer call
that happens to have a null DID. The `agent_did_source: null`
field helps (peer calls from unpinned observed-failed peers also
have it null) but doesn't cleanly partition.
**Fix:** add an explicit `tool_kind: "peer" | "local"` field on
the task.* SSE frames.
**Workaround:** Filter on `agent === "load_recipe"` client-side.
**Tracking:** _(no issue yet)_

### recipe-file-enumeration-no-truncation-signal

**Severity:** low
**Summary:** The
[`load_recipe`](../gateway/src/tool/recipe.ts) tool returns a
`<recipe_files>` block listing sibling files inside a bundled
recipe's directory, capped at 10 entries. If a recipe directory
has more than 10 files, the excess silently disappears from the
list — the planner has no way to know it's seeing a sample, not
the full set.
**Fix:** include an explicit `truncated: true` marker in the tool
result's metadata, and emit a `console.warn` at boot when a recipe
directory exceeds the cap.
**Workaround:** Keep bundled recipe directories under 10 files.
**Tracking:** _(no issue yet)_

### faq-agent-did-name-mismatch

**Severity:** low
**Summary:** The fleet demo's
[`examples/gateway_test_fleet/faq_agent.py`](../examples/gateway_test_fleet/faq_agent.py)
registers its DID as `bindu_docs_agent` but the filename and the
operator-facing port labels (3778) say `faq_agent`. First-time
readers following `docs/GATEWAY.md` Chapter 3 see the mismatch in
the SSE `agent_did` strings vs the catalog `agent` field and
wonder if something is wrong. Python-side concern, no gateway code
involved.
**Workaround:** The mismatch is cosmetic — signature verification
and routing both work. Ignore or pin `faq_agent` DID explicitly in
the catalog.
**Tracking:** _(no issue yet)_

### fleet-env-can-desync-after-seed-rotation

**Severity:** low
**Summary:**
[`examples/gateway_test_fleet/start_fleet.sh`](../examples/gateway_test_fleet/start_fleet.sh)
writes fresh DIDs to `.fleet.env` on every run. But if an agent's
seed rotates (`rm -rf ~/.bindu`, restart) and a user has an old
shell with `$RESEARCH_DID` still sourced from a prior `.fleet.env`,
their next `/plan` pins a stale DID. Signature verification fails
with a cryptic mismatch error.
**Fix:** have `start_fleet.sh` print a "re-source `.fleet.env` if
you had one loaded previously" hint whenever any agent's DID
differs from the previous run's cache.
**Workaround:** Always `source .fleet.env` fresh after any fleet
restart.
**Tracking:** _(no issue yet)_

### provider-openrouter-hardcoded

**Severity:** low
**Summary:**
[`gateway/src/provider/index.ts`](../gateway/src/provider/index.ts)
and downstream code assume the `openrouter/` model prefix. Adding
direct Anthropic or direct OpenAI support (without going through
OpenRouter's proxy) is a code change, not config.
**Workaround:** Use OpenRouter as the universal proxy; it supports
every major provider. Only reach for this when you need direct
provider features (e.g. Anthropic prompt caching, OpenAI
fine-tuned model access) that OpenRouter doesn't proxy.
**Tracking:** _(no issue yet)_

### accept-header-not-enforced-on-plan

**Severity:** nit
**Summary:** `POST /plan` returns `text/event-stream` regardless
of whether the client sent `Accept: text/event-stream`. Clients
that forget the header still get SSE, which is convenient but
breaks strict content-negotiation semantics. Not currently
documented as required in
[`openapi.yaml`](../gateway/openapi.yaml) either.
**Fix:** either document the header as required and return 406
when absent, or keep the permissive behavior and document it.
Currently we're in the worst middle ground.
**Workaround:** None needed; current behavior is operationally
fine. Consumers relying on strict 406 on wrong `Accept` won't get
it.
**Tracking:** _(no issue yet)_

### openapi-sse-schemas-unused

**Severity:** nit
**Summary:** `redocly lint gateway/openapi.yaml` reports 13
`no-unused-components` warnings on the `SSEEvent_*` schemas.
OpenAPI 3.1 has no native SSE modeling, so those schemas sit as
reference material rather than being `$ref`'d from a response
body. The warnings are expected given the format's limitations,
not indicative of drift.
**Fix options:** (a) accept — pragmatic, 0 errors, just warnings;
(b) use `oneOf` inside the `text/event-stream` response schema to
enumerate each event shape (stretches OpenAPI); (c) publish a
separate AsyncAPI 2.x/3.x spec for the SSE surface.
**Workaround:** None needed; warnings don't break consumers.
**Tracking:** _(no issue yet)_

### no-planner-integration-test

**Severity:** nit
**Summary:** The unit tests cover every Gateway module in
isolation, but no single test walks a `/plan` request
end-to-end with a mocked LLM provider. The recipes feature,
signatures surfacing, and observed-DID resolution were all
verified manually against the real stack and via targeted unit
tests for their pure helpers. A regression in the cross-cutting
glue (tool → Bus → SSE JSON) would be caught only at integration
time.
**Fix:** mock `Provider.Service` with a fake emitting a canned
`StreamEvent` sequence; assert SSE output matches expectations.
**Workaround:** None — treat this as internal backlog.
**Tracking:** _(no issue yet)_

### no-health-handler-integration-test

**Severity:** nit
**Summary:**
[`tests/api/health-route.test.ts`](../gateway/tests/api/health-route.test.ts)
covers only the pure helpers (`splitModelId`, `deriveGatewayId`,
`deriveAuthor`). The handler's full response shape — version,
planner-model nesting, runtime flags, uptime math — is verified
by manual curl, not by a test that builds the layer graph and
asserts the JSON. Drift between `openapi.yaml`'s `HealthResponse`
schema and the actual response would go unnoticed until someone
hand-checks.
**Fix:** build a minimal layer graph (mock Supabase) in a test,
invoke the handler against a stub Hono context, assert the body
matches the openapi schema.
**Workaround:** Manual curl against a running gateway.
**Tracking:** _(no issue yet)_

### story-chapter5-missing-oauth-scope-explanation

**Severity:** nit
**Summary:**
[`docs/GATEWAY.md`](../docs/GATEWAY.md) Chapter 5 sets
`BINDU_GATEWAY_HYDRA_SCOPE` via env vars but never explains what
OAuth scopes are or why `agent:read` + `agent:write` are the
defaults. A reader walking the story linearly hits the config
step without context.
**Fix:** one-paragraph sidebar in Chapter 5 explaining "scopes
are labels we ask Hydra to stamp on tokens; peers check them
before accepting a `message/send`".
**Workaround:** Cross-ref to gateway/README.md §DID signing which
explains it.
**Tracking:** _(no issue yet)_

---

## Bindu Core (Python)

### Quick index

| Slug | Severity | One-line |
|---|---|---|
| [`x402-middleware-fails-open-on-body-parse`](#x402-middleware-fails-open-on-body-parse) | high (sec) | Malformed body parse lets request through without payment |
| [`x402-no-replay-prevention`](#x402-no-replay-prevention) | high (sec) | Payment proofs are reusable until `validBefore` |
| [`x402-no-signature-verification`](#x402-no-signature-verification) | high (sec) | EIP-3009 authorization signature is never verified |
| [`x402-balance-check-skipped-on-missing-contract-code`](#x402-balance-check-skipped-on-missing-contract-code) | high (sec) | Missing RPC contract-code silently skips balance check |
| [`authz-scope-check-behind-optional-flag`](#authz-scope-check-behind-optional-flag) | medium (sec) | Scope check is optional; flipping the flag removes all authz |
| [`did-admission-control-missing`](#did-admission-control-missing) | medium (sec) | No allowlist — any Hydra-registered DID can call |
| [`cors-allow-credentials-with-user-origins`](#cors-allow-credentials-with-user-origins) | medium (sec) | Credentials + loose origins risk credentialed CORS |
| [`hydra-token-cache-revocation-lag`](#hydra-token-cache-revocation-lag) | medium (sec) | Revoked tokens valid for up to 5 min |
| [`task-cancel-check-then-act-race`](#task-cancel-check-then-act-race) | medium | TOCTOU between state check and scheduler cancel |
| [`no-rate-limit-or-quota-per-caller`](#no-rate-limit-or-quota-per-caller) | medium | No per-caller quota; single caller can exhaust resources |
| [`context-id-silent-fallback`](#context-id-silent-fallback) | medium | Malformed `context_id` silently creates a new context |
| [`artifact-name-not-sanitized`](#artifact-name-not-sanitized) | low (sec) | Agent-supplied artifact names not basenamed |

### High

### x402-middleware-fails-open-on-body-parse

**Severity:** high (security, payment bypass)

> **Scenario.** An attacker sends a malformed JSON body (truncated,
> wrong encoding, bad UTF-8) to a x402-protected endpoint. Python's
> `json.loads` throws. The middleware's bare `except Exception:`
> catches it — and calls `await call_next(request)` anyway. The
> request reaches the agent. The agent runs. No payment was checked.

**What's wrong.** The x402 payment middleware at
[`bindu/server/middleware/x402/x402_middleware.py`](../bindu/server/middleware/x402/x402_middleware.py)
lines 213–215 wraps the initial JSON-RPC body parse in
`except Exception` and calls `call_next(request)` on failure. Any
client that can cause the parse to throw reaches the agent without
a payment check. The bare `except` also masks real bugs during
parsing. Adjacent concern: the subsequent check is
`if method not in app_settings.x402.protected_methods`, so a
request that parses but reports an unknown method also bypasses
payment.

**Workaround.** Configure x402 only when no protected methods can
be avoided by crafting the request body; otherwise treat the x402
middleware as advisory. The fix is to return a 402 response on
parse failure and narrow the exception to `json.JSONDecodeError`
and `UnicodeDecodeError`.

**Tracking:** _(no issue yet)_

### x402-no-replay-prevention

**Severity:** high (security, payment bypass)

> **Scenario.** Alice pays $10 once. The server returns her a
> payment token. She puts it in `X-PAYMENT` for Request A — valid,
> task runs, she's charged $10 on-chain. She puts the **same token**
> in `X-PAYMENT` for Request B — still valid, task runs, **no
> additional charge.** And Request C. And D. All until the
> `validBefore` window closes (seconds to minutes). One payment
> buys unlimited work.

**What's wrong.** `_validate_payment_manually` in
[`bindu/server/middleware/x402/x402_middleware.py`](../bindu/server/middleware/x402/x402_middleware.py)
lines 282–394 performs five checks (scheme, authorization presence,
amount-minimum, network match, on-chain balance) but never records
or looks up the `(nonce, payer)` or `(txhash, chain)`. The same
`X-PAYMENT` header is accepted on every request and the payment
session token returned by
[`bindu/server/endpoints/payment_sessions.py`](../bindu/server/endpoints/payment_sessions.py)
is never marked consumed.

**Workaround.** Set short `validBefore` windows on the EIP-3009
authorization issued to clients, reducing the replay window to
seconds. The real fix is to persist `(nonce, payer_address)` in a
dedupe store (Redis `SETNX` keyed by nonce, TTL ≥ `validBefore`)
and reject any payload whose nonce is already present.

**Tracking:** _(no issue yet)_

### x402-no-signature-verification

**Severity:** high (security, payment forgery)

> **Scenario.** Mallory looks up Alice's public wallet address
> on-chain (it's public). She knows Alice holds USDC. Mallory
> constructs a plausible-looking EIP-3009 `TransferWithAuthorization`
> payload claiming Alice's address as payer, with any amount she
> wants, **and any signature bytes she feels like pasting in.** She
> sends it to the agent. The middleware checks: scheme ✓, network
> ✓, amount ✓, Alice has a balance ✓ — **never verifies the
> signature.** Request accepted. Mallory gets work; Alice sees no
> charge (the forged authorization doesn't clear on-chain) but the
> agent burned its compute anyway.

**What's wrong.** The validation routine at
[`bindu/server/middleware/x402/x402_middleware.py`](../bindu/server/middleware/x402/x402_middleware.py)
lines 282–394 checks amount, network, and payer balance but never
verifies the EIP-3009 `TransferWithAuthorization` signature against
the payer's address. The docstring at line 292 even labels the
signature check "optional" — and the actual call doesn't verify it.
Combined with `x402-no-replay-prevention`, there is no
cryptographic binding between the caller and the payment.

**Workaround.** Do not rely on x402 for revenue protection in the
current release. If revenue matters, sit x402 behind a proxy that
verifies the signature out-of-band, or disable x402 and use a
pre-paid credits model backed by an authenticated account. The fix
is to call `eth_account.Account.recover_message` (or equivalent) on
the EIP-3009 typed-data digest and reject if the recovered address
does not match `auth.from_`.

**Tracking:** _(no issue yet)_

### x402-balance-check-skipped-on-missing-contract-code

**Severity:** high (security, payment bypass)

> **Scenario.** An operator sets `payment_requirements.asset` to the
> wrong USDC contract address (typo, wrong chain). Or their RPC
> provider has a transient outage and `eth.get_code()` returns empty
> bytes. The middleware notices "no contract at this address" and
> logs `"Skipping balance check"` — then **returns `True`** (valid
> payment). An attacker with a zero-balance address can pay and get
> work.

**What's wrong.**
[`bindu/server/middleware/x402/x402_middleware.py`](../bindu/server/middleware/x402/x402_middleware.py)
lines 348–352 skip the on-chain balance check when
`w3.eth.get_code` returns empty bytes. A misconfigured
`payment_requirements.asset`, a transient RPC fault, or an operator
pointing at a fork where the token is not yet deployed all cause
the balance check to silently no-op. The outer `except Exception`
at line 377 correctly fails closed if the balance call itself
throws, but the "no code" branch is a logged warning and a
fall-through to `return True`.

**Workaround.** Monitor logs for
`"No contract found at … Skipping balance check"` — if it appears
in production, payment is effectively disabled. Pin a known-good
RPC endpoint and verify the token address on startup. The fix is
to reject payment (not skip) when the contract is not found, and
to validate `asset` against a hardcoded list of known USDC
addresses per chain at startup.

**Tracking:** _(no issue yet)_

### Medium

### authz-scope-check-behind-optional-flag

**Severity:** medium (security, authorization)
**Summary:** The scope check in
[`bindu/server/endpoints/a2a_protocol.py`](../bindu/server/endpoints/a2a_protocol.py)
line 153 is wrapped in
`if app_settings.auth.require_permissions:`. When the flag is falsy
(common during bringup, demos, or debugging), the A2A endpoint
accepts any authenticated token for any method — there is no
authorization layer at all, only authentication. Authorization being
a feature flag is a deployment landmine: an operator who turns it
off to "unblock" something forgets to turn it back on and ships a
scopeless service.
**Workaround:** Always deploy with `require_permissions: true` and
define per-method scopes in `auth.permissions`. Treat the flag as
deprecated in your configuration and add a startup assertion that
refuses to boot when the flag is false and auth is enabled.
**Tracking:** _(no issue yet)_

### did-admission-control-missing

**Severity:** medium (security, admission control)
**Summary:**
[`bindu/server/middleware/auth/hydra.py`](../bindu/server/middleware/auth/hydra.py)
verifies that an inbound request was signed by the private key of
the DID declared in the OAuth token's `client_id`. Crypto is
correct: forging signatures for a known DID is not feasible. But
there is no admission-control layer above that — the server trusts
ANY Hydra-registered DID that presents a valid OAuth token and a
valid signature. No allowlist, no trust-chain check, no pattern
match against an expected DID namespace.

Concretely: in a multi-tenant deployment (or one where Hydra's
admin API is reachable by more than the operator), a third party
can `hydra create oauth2-client` with `client_id=did:bindu:evil:*`
and a public key they control, then call the agent. Their token
validates (Hydra issued it), their signature validates (they hold
the matching private key), and the request reaches the handler.

What they gain:

- Ability to submit tasks — the agent burns its compute / LLM
  budget executing on their behalf.
- The response stream — they get whatever the agent produces.

What they cannot do (already mitigated):

- Read other tenants' tasks — PR #460
  (`idor-task-context-no-ownership-check`, see postmortem
  [`2026-04-18-idor-task-ownership.md`](./core/2026-04-18-idor-task-ownership.md))
  scopes reads and lists by `owner_did`. Rows they create are only
  visible to them.

Single-tenant deployments with locked-down Hydra admin access are
not reachable by this; Hydra registration is the de facto trust
boundary. Severity rises to high for SaaS / multi-tenant / shared
Hydra shapes.

**Workaround:** Tightly restrict Hydra admin API access to the
operator; audit the list of registered OAuth clients before
exposing the agent. For stronger posture, deploy behind a reverse
proxy that filters incoming `Authorization` headers by a known
allowlist of token introspection subjects, or add a small
post-auth middleware that rejects the request when
`client_did not in app_settings.auth.allowed_dids`. A native fix
would add an `ALLOWED_DIDS` config (exact-match or pattern) to
`app_settings.auth` and enforce it in the Hydra middleware after
signature verification passes — ~30 lines in one file.
**Tracking:** _(no issue yet)_

### cors-allow-credentials-with-user-origins

**Severity:** medium (security, CORS misconfig)
**Summary:**
[`bindu/server/applications.py`](../bindu/server/applications.py)
lines 563–571 instantiate `CORSMiddleware` with
`allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`,
and `allow_origins=cors_origins` where `cors_origins` is an
operator-supplied list. Starlette does reject the literal wildcard
`["*"]` with credentials, but an operator passing
`["https://example.com", "null"]`, a reflected-origin scheme, or
simply an over-broad list (every internal tool) still gets a
credentialed cross-origin surface. There is no startup assertion
that the supplied origins are compatible with `allow_credentials=True`.
**Workaround:** Set `cors_origins` to an exhaustive, minimal list
of known origins. Never include `"null"`, `"*"`, or a
reflected-origin scheme. If possible, terminate CORS at a reverse
proxy and leave `cors_origins=None` on the Bindu app.
**Tracking:** _(no issue yet)_

### hydra-token-cache-revocation-lag

**Severity:** medium (security, revocation)
**Summary:** The Hydra middleware caches introspection results for
up to 300 s (`CACHE_TTL_SECONDS = 300`) in
[`bindu/server/middleware/auth/hydra.py`](../bindu/server/middleware/auth/hydra.py).
Revoking a token in Hydra does not clear this in-process cache, so
revoked tokens remain valid for up to five minutes across all Bindu
instances that already cached them. For sensitive operations
(admin, payment capture, key rotation) that window is too long.
**Workaround:** Reduce `CACHE_TTL_SECONDS` for high-risk
deployments, or disable the cache for specific scopes. The fix is a
revocation callback from Hydra (or a short TTL with aggressive
eviction) that invalidates the cache entry on `revoke_token`.
**Tracking:** _(no issue yet)_

### task-cancel-check-then-act-race

**Severity:** medium (correctness, concurrency)
**Summary:**
[`bindu/server/handlers/task_handlers.py`](../bindu/server/handlers/task_handlers.py)
lines 67–95 load the task, read `status.state`, compare against
`app_settings.agent.terminal_states`, and then call
`self.scheduler.cancel_task(...)` without any atomic update between
the read and the write. A worker that completes the task between
those two steps leaves `cancel_task` trying to cancel a task that
already reached a terminal state — the resulting behavior depends
on the scheduler implementation and is not deterministic. The
second `load_task` at line 90 may return a terminal task with the
cancellation ignored, misleading the caller.
**Workaround:** Callers should treat `cancel_task` as best-effort
and always re-check task state after the call returns. Fix is a
compare-and-swap in storage (`update_task_state_if(from, to)`) that
returns false when the state has already moved.
**Tracking:** _(no issue yet)_

### no-rate-limit-or-quota-per-caller

**Severity:** medium (DoS)
**Summary:** The A2A endpoint, the scheduler, and `ManifestWorker`
all run without per-caller quotas or global concurrency caps. A
single authenticated DID can fire `message/send` in a loop and
exhaust the scheduler queue, storage writes, and memory (tasks are
kept hot for fast lookup). Request-body size is also uncapped on
the Bindu app (Starlette default, no explicit limit). Nothing in
`bindu/server/applications.py` or
`bindu/server/endpoints/a2a_protocol.py` imposes rate limits,
per-caller task caps, or a worker-pool semaphore.
**Workaround:** Deploy behind a reverse proxy (nginx, Cloudflare,
API Gateway) that enforces request-rate and body-size limits per
client IP or DID. Operators running Bindu directly on the public
internet are currently exposed. The fix is per-DID quotas enforced
at the `TaskManager.send_message` level plus an explicit body-size
limit on the Starlette app.
**Tracking:** _(no issue yet)_ (shape-equivalent to the gateway's
`no-rate-limit-cors-body-size-limit` entry)

### context-id-silent-fallback

**Severity:** medium (correctness, silent data loss)
**Summary:** `_parse_context_id` in
[`bindu/server/task_manager.py`](../bindu/server/task_manager.py)
lines 196–216 logs a warning and returns a fresh UUID when the
client sends a malformed `context_id`. The caller believes they are
continuing conversation X and actually start a new isolated one;
the old context is orphaned in storage. This also gives an attacker
a cheap way to inflate storage by sending thousands of malformed
context IDs.
**Workaround:** Clients must validate `context_id` before sending.
The fix is to reject malformed UUIDs with a JSON-RPC error
(-32602 "Invalid params") rather than fabricate a new one.
**Tracking:** _(no issue yet)_

### Low

### artifact-name-not-sanitized

**Severity:** low (security, path handling)
**Summary:** `Artifact.from_result` in
[`bindu/utils/worker/artifacts.py`](../bindu/utils/worker/artifacts.py)
accepts an `artifact_name` passed from the agent manifest and
persists it verbatim without any basename or character filtering.
If a downstream storage backend constructs a filesystem path from
that name (current Postgres storage does not, but any file-based or
S3-prefixed backend would), an agent that returns
`artifact_name="../../etc/passwd"` writes outside the expected
directory. Defensive sanitization is cheap and the surface is
visible.
**Workaround:** Operators running a file-backed artifact store
should apply `os.path.basename` and an allow-list regex before
writing. Fix in-core is to sanitize in `from_result`:
`artifact_name = os.path.basename(artifact_name) or "result"`.
**Tracking:** _(no issue yet)_

---

## SDKs (TypeScript)

_No entries yet. Add them when the TS SDK's review pass lands. New
postmortems for fixed SDK bugs go in [`bugs/sdk/`](./sdk/)._

---

## Frontend

_No entries yet. New postmortems for fixed frontend bugs go in
[`bugs/frontend/`](./frontend/)._
