---
id: 2026-04-18-types-populate-by-name
title: Server rejected snake_case input even though Python types used snake_case attributes
severity: medium
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: bindu/common/protocol
commit: (this PR)
pr:
issue:
---

## Symptom

A developer writing a Python client against Bindu reads
[`bindu/common/protocol/types.py`](../../bindu/common/protocol/types.py)
and sees every TypedDict declared with idiomatic Python attribute
names:

```python
@pydantic.with_config(ConfigDict(alias_generator=to_camel))
class Message(TypedDict):
    message_id: Required[UUID]
    context_id: Required[UUID]
    task_id:    Required[UUID]
```

They construct a request with the same keys the Python types
advertise:

```python
body = {
    "jsonrpc": "2.0",
    "id": "…",
    "method": "message/send",
    "params": {
        "message": {
            "kind": "message",
            "message_id": "…",
            "context_id": "…",
            "task_id":    "…",
            "role": "user",
            "parts": [{"kind": "text", "text": "hi"}],
        }
    },
}
httpx.post(agent_url, json=body)
```

The server responds with a 400 validation error:

```
params.message.messageId: Field required
params.message.contextId: Field required
params.message.taskId:    Field required
```

Three fields the developer *did* send, referred to by keys the Python
code never mentions (camelCase aliases, not the Python attribute
names), declared missing. Their autocompletion, their mypy types,
their `dir()` inspection all pointed at snake_case; the server's
error message insists on camelCase; their snake_case keys were
silently discarded before the missing-field check ran.

## Root cause

Pydantic's `ConfigDict` has two separate knobs that control
alias behavior:

- `alias_generator=to_camel` — *generate* an alias for each field
  (`message_id` → `messageId`).
- `populate_by_name=True` — on input, *accept* either the alias
  OR the Python attribute name.

Bindu's
[`types.py`](../../bindu/common/protocol/types.py) set the first but
not the second. The default for `populate_by_name` is `False`, which
means "accept the alias only." The Python attribute names the types
file declared were unreachable by design — they existed for the
Python side of the mapping, but pydantic refused to populate a field
using them.

Output side was also controlled separately: the server dumps
responses with `by_alias=True` in
[`a2a_protocol.py`](../../bindu/server/endpoints/a2a_protocol.py), so
the wire format on responses was correctly camelCase — consistent
with A2A spec v0.3.0, the TypeScript SDK, the Postman collection,
and the deployed OpenAPI specs.

So on-the-wire Bindu was strictly spec-compliant; the bug was
purely in input tolerance. A client that sent what the external
protocol expects (camelCase) worked fine. A client that sent what
the Python types locally advertised (snake_case) did not. Two
different contracts, visible from different sides of the same
file, and the one less visible to Python developers was the one
that won.

## Fix

Two changes in
[`bindu/common/protocol/types.py`](../../bindu/common/protocol/types.py):

1. Introduce a named shared config at the top of the module:

   ```python
   A2A_MODEL_CONFIG = ConfigDict(
       alias_generator=to_camel,
       populate_by_name=True,
   )
   ```

   A named constant beats 59 inline `ConfigDict(...)` declarations —
   the next time the config needs to change, we edit one line, not
   59.

2. Replace every `@pydantic.with_config(ConfigDict(alias_generator=to_camel))`
   with `@pydantic.with_config(A2A_MODEL_CONFIG)` — mechanical find-
   and-replace across all 59 TypedDict decorators.

No signatures change. No wire format changes. Output stays
camelCase because `by_alias=True` at the serializer is unchanged.
The only observable effect is that a Python client sending
snake_case now gets accepted instead of rejected.

The fix ships with 9 dedicated tests in
[`tests/unit/common/test_types_populate_by_name.py`](../../tests/unit/common/test_types_populate_by_name.py):

- Guard that `A2A_MODEL_CONFIG` has both `populate_by_name=True`
  and the alias generator set, so a future accidental drop of the
  flag is caught.
- Input tolerance: ``Message`` and ``Artifact`` both accept snake_case
  and camelCase; full ``a2a_request_ta.validate_json`` — the exact
  entry point the server uses — accepts a deep snake_case request
  (including a snake_case key inside the nested ``configuration``
  sub-object).
- Output contract: after validating a snake_case input, dumping
  with ``by_alias=True`` produces camelCase-only output.
  ``messageId``/``contextId``/``taskId`` always present on the wire;
  their snake_case forms never.

All 776 pre-existing unit tests continue to pass unchanged. The
fix is strictly additive on input (more accepting) and a no-op on
output.

## Why the tests didn't catch it

Every existing test either used the server's internal Python
attribute-name access (``task["id"]``, ``task["context_id"]``) or
constructed test payloads by hand with camelCase because the
developer had already absorbed the workaround. None exercised the
path a *new* Python client would take — building a request using
the attribute names the Python types declare and sending it over
HTTP. Had such a test existed, the asymmetry would have been
caught immediately.

The new ``test_full_a2a_request_accepts_snake_case`` test drives
``a2a_request_ta.validate_json(json.dumps(...))`` with a fully
snake_case payload — the exact entry point
[`a2a_protocol.py:129`](../../bindu/server/endpoints/a2a_protocol.py)
uses. Future regressions on this path will fail in CI instead of
in a developer's first-ten-minutes experience with the SDK.

## Class of bug — where else to watch

Two related shapes to scan for in this codebase and others:

- **Alias generator without `populate_by_name`**. Anywhere a
  `ConfigDict(alias_generator=...)` is written, the question "what
  happens if an API client sends the non-aliased form?" should
  have a deliberate answer. The default (strict alias) is usually
  the wrong one for a public-facing API consumed by clients in the
  same language whose conventions differ from the wire format.
- **Types that advertise names they don't accept.** More generally
  — if a type's public attribute names are not the same as its
  serialization keys, and the discrepancy is only visible in a
  separate config object, a Python developer will read the type
  and expect the attribute names to work. Shared module-level
  config objects (like ``A2A_MODEL_CONFIG``) are easier to audit
  than 59 inline declarations because there's one place to look.

Adjacent code to audit with the same question:

- Any gRPC protobuf-to-JSON mapping. Proto files use snake_case by
  convention; JSON mapping defaults to camelCase but is
  configurable. Check [`proto/agent_handler.proto`](../../proto/agent_handler.proto)
  and any language SDK that stringifies proto messages for REST
  endpoints — the same "wire format vs. language format" decision
  arises there.
- Any future REST endpoints layered on top of these types. They
  inherit this fix automatically because they share ``types.py``,
  but if new types are added in another module they need their own
  ``populate_by_name=True`` (or the shared config imported and
  reused).

## Follow-ups

- Document the accepted input convention in the public API
  reference: "snake_case and camelCase both accepted; responses
  are always camelCase." Avoids future developers rediscovering
  this tolerance via trial and error.
- The DID extension endpoint at
  [`bindu/server/endpoints/did_endpoints.py`](../../bindu/server/endpoints/did_endpoints.py)
  returns the raw DID document dict without routing through a
  pydantic TypeAdapter. For W3C DID docs that's correct (their
  schema uses the W3C spec key names), but any Bindu-internal
  extension fields would leak out as snake_case. Tracked separately
  as `did-document-endpoint-returns-raw-dict` in
  [`bugs/known-issues.md`](../known-issues.md).
