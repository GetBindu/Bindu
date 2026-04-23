---
id: 2026-04-18-idor-task-ownership
title: Any authenticated caller could read or mutate another caller's tasks and contexts
severity: critical
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: bindu/server
commit: d664e1e
pr:
issue:
---

## Symptom

In any Bindu deployment with more than one authenticated caller —
e.g. two customers running their own agents behind a shared Bindu
instance, or a SaaS provider hosting one agent for many tenants —
a valid bearer token was sufficient to read, cancel, or destroy
another caller's tasks and contexts over the A2A JSON-RPC API.

Concretely, Bob (authenticated with his own valid Hydra token)
could:

- Call `tasks/list` and receive every task stored by the server,
  including Alice's prompts, her agent's replies, and any attached
  artifacts. No UUID enumeration required — the response paginated
  over the entire table.
- Call `tasks/get` with any task UUID he learned or guessed and
  receive Alice's full task body.
- Call `tasks/cancel` on Alice's in-flight task.
- Call `contexts/clear` on Alice's context, destroying the full
  conversation thread including its task rows.
- Call `message/send` referencing Alice's `context_id`, splicing
  his own messages into her conversation.
- Register a webhook on Alice's task via
  `tasks/pushNotification/config/set` and receive all lifecycle
  events for her execution.

The auth middleware (Ory Hydra OAuth2) correctly identified *who*
Bob was. Nothing downstream ever asked whether Bob was allowed to
touch *that particular* row.

## Root cause

The bug was not a single buggy line — it was a missing concept. The
storage layer had no notion of task ownership, and the handlers
never consulted the caller's identity when serving a request.

Pre-fix state at
[`bindu/server/handlers/task_handlers.py:51-62`](../../bindu/server/handlers/task_handlers.py):

```python
async def get_task(self, request: GetTaskRequest) -> GetTaskResponse:
    task_id = request["params"]["task_id"]
    history_length = request["params"].get("history_length")
    task = await self.storage.load_task(task_id, history_length)
    if task is None:
        return self.error_response_creator(...)
    return GetTaskResponse(jsonrpc="2.0", id=request["id"], result=task)
```

Count the places the caller's identity appears: zero. The same
shape held across `cancel_task`, `list_tasks`, `task_feedback`,
`list_contexts`, `clear_context`, and the four
push-notification handlers. `storage.list_tasks(length)` was a
global query with no `WHERE` clause.

Why did it ship this way? The server was designed around two
orthogonal concepts that never intersected:

- **Authentication** ("who is this caller?") — implemented as a
  Hydra ASGI middleware that attached `user_info` to
  `scope.state.user`.
- **Task routing** ("dispatch by method name") — implemented in
  the A2A endpoint as `getattr(task_manager, handler_name)` with no
  user context passed along.

The endpoint trusted the middleware to answer "should this caller
reach this method at all?" (scope-gated, and even that was behind
an optional `require_permissions` flag). Row-level authorization
— the part every multi-tenant system needs — was simply missing.
No bug in any one file; a bug in the contract between files.

## Fix

Landed in four phases on branch `fix/task-ownership-idor`, each
self-contained and deployable independently so the rollout could
be incremental:

**Phase 1 — plumbing** (commits `2101d6d`, `bb97d13`)

- New nullable `owner_did` column + index on `tasks` and
  `contexts` ([`bindu/server/storage/schema.py`](../../bindu/server/storage/schema.py))
- Alembic migration [`20260418_0001_add_owner_did.py`](../../alembic/versions/20260418_0001_add_owner_did.py)
- `Storage` ABC gained `get_task_owner` / `get_context_owner`
  and `submit_task(caller_did=...)`
- A2A endpoint resolves `caller_did` from
  `scope.state.user.client_id` and threads it through every
  `TaskManager` handler method. Every handler now carries the
  caller's identity; enforcement landed separately.

**Phase 2 — enforcement** (commits `9424272`, `d664e1e`)

- `storage.submit_task` raises `OwnershipError` when the
  referenced context exists with a different owner; handlers
  translate to `ContextNotFoundError` on the wire so existence
  cannot be probed across tenants.
- `list_tasks` / `list_contexts` / `list_tasks_by_context` accept
  an optional `owner_did` filter that hits the new indexes.
- `get_task`, `cancel_task`, `task_feedback`, `clear_context`,
  and all four push-notification handlers compare
  `get_*_owner(id)` vs `caller_did` and return
  `TaskNotFoundError` / `ContextNotFoundError` on mismatch.

**Phase 3 — operator tooling** (commit `7db5945`)

- [`scripts/backfill_owner_did.py`](../../scripts/backfill_owner_did.py) assigns pre-existing NULL-owner
  rows to a designated DID before enforcement is deployed.
- [`alembic/README.md`](../../alembic/README.md) documents the
  upgrade ordering: migrate → backfill → deploy enforcement.

**Phase 4 — regression coverage + cleanup**

- Integration test [`tests/integration/test_task_ownership.py`](../../tests/integration/test_task_ownership.py)
  drives the real `TaskManager` with two synthetic DIDs and
  asserts cross-tenant denial on every public handler (10 cases).
- This postmortem.
- The `idor-task-context-no-ownership-check` entry removed from
  [`bugs/known-issues.md`](../known-issues.md).

## Why the tests didn't catch it

Every existing handler test in
[`tests/unit/server/handlers/`](../../tests/unit/server/handlers/)
exercised a single synthetic caller with mocked storage. There
was no "two tenants" scenario — no test where task A was created
by one identity and then fetched by another. The handler returned
the row because the mock returned the row, and the test passed
because the assertion only checked the response shape.

The integration tests for gRPC
([`tests/integration/grpc/test_grpc_e2e.py`](../../tests/integration/grpc/test_grpc_e2e.py))
likewise ran one caller end-to-end. Auth was either disabled or
mocked out, so `scope.state.user` was whatever the test supplied.

Access-control bugs are particularly invisible to single-actor
tests — they *only* manifest when an actor touches something that
another actor created. The fix includes exactly that: every new
test in the integration suite performs an action as one DID and
asserts the opposite DID cannot see or mutate the result.

## Class of bug — where else to watch

IDOR / missing row-level authz is a *shape* that can hide in any
handler that accepts an ID from the request and returns data
keyed by it. Audit anywhere the pattern `load_by_id(user_input)`
appears without an adjacent ownership check. In this codebase:

- [`bindu/server/endpoints/negotiation.py:220`](../../bindu/server/endpoints/negotiation.py) —
  `app.task_manager.storage.list_tasks()` is called with no
  owner filter. The negotiation endpoint is on a different auth
  path and wasn't in scope for this fix, but the same row-level
  authz question applies: can peer A negotiate over peer B's
  task inventory? Worth a follow-up audit.
- [`bindu/server/endpoints/metrics.py:43-49`](../../bindu/server/endpoints/metrics.py) —
  `count_tasks(status=...)` returns a global count across all
  tenants. For aggregate operational metrics this is acceptable,
  but if metrics are ever exposed per-caller (e.g. a "your usage"
  endpoint) the same shape would leak tenant sizes. Flag this
  before any such change.
- [`bindu/extensions/`](../../bindu/extensions/) — any future
  extension that attaches to a task ID (x402 payment sessions,
  skills registration, etc.) should verify the caller owns the
  task before allowing the attachment. The push-notification
  enforcement in this fix is the reference pattern.
- The per-DID schema feature from
  [`20260119_0001_add_schema_support.py`](../../alembic/versions/20260119_0001_add_schema_support.py)
  isolates agents (each agent's own DID gets its own schema) but
  still shares a schema across all the *callers* of that agent.
  The `owner_did` column added by this fix is required inside
  every DID schema; the `create_bindu_tables_in_schema` stored
  procedure has not yet been updated to include it, so existing
  DID schemas need a manual `ALTER TABLE ... ADD COLUMN
  owner_did VARCHAR(255)` + index. Tracked as a follow-up below.

## Follow-ups

- Update `create_bindu_tables_in_schema` so DID-specific schemas
  created after this fix pick up `owner_did` automatically.
- Add row-level owner filtering to the negotiation endpoint (or
  document explicitly why global listing is correct there).
- The authz scope-enforcement flag
  (`auth.require_permissions`) remains optional — see slug
  `authz-scope-check-behind-optional-flag` in
  [`bugs/known-issues.md`](../known-issues.md). Row-level
  ownership and scope-based authz are complementary; both
  belong on by default in production.
