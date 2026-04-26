---
id: 2026-04-19-did-document-endpoint-raw-dict
title: DID resolution endpoint bypassed the camelCase wire contract
severity: low
status: fixed
found: 2026-04-18
fixed: 2026-04-19
area: bindu/server/endpoints
commit: (this PR)
pr:
issue:
---

## Symptom

A peer discovering a Bindu agent via `/did/resolve` received a
JSON-LD DID document formatted to the W3C spec:

```json
{
  "@context": ["https://www.w3.org/ns/did/v1", "https://getbindu.com/ns/v1"],
  "id":  "did:bindu:raahul_dutta_at_example_com:joke_agent:...",
  "created": "2026-04-19T13:20:01.976492+00:00",
  "authentication": [{
    "id":  "did:bindu:...#key-1",
    "type": "Ed25519VerificationKey2020",
    "controller": "did:bindu:...",
    "publicKeyBase58": "7dNzT2ZzYKsibUFirPVWZheh2TGKZuy3fGdCkcq2f2RM"
  }]
}
```

All keys were correct — `@context`, `publicKeyBase58`, etc. Nothing
observable broke. But the endpoint's output path was *structurally*
different from every other A2A endpoint: it called
`JSONResponse(content=did_document)` with the dict the DID
extension returned, no aliasing, no validation. Every other A2A
endpoint in the codebase routes its payload through pydantic's
`by_alias=True` serialization so snake_case Python attribute names
become camelCase on the wire.

That meant: the day anyone added a Bindu-specific field to
`get_did_document()` using Python-idiomatic snake_case — say, a
`service_endpoint`, `agent_trust`, or `key_agreement` block — the
field would leak onto the wire in snake_case. Strict A2A tooling
downstream would see an inconsistent document and either misparse
or reject.

Low-severity, but the kind of latent bug that becomes a real
compatibility break once someone touches the extension.

## Root cause

At [`bindu/server/endpoints/did_endpoints.py:97`](../../bindu/server/endpoints/did_endpoints.py)
(pre-fix):

```python
did_document = did_extension.get_did_document()
return JSONResponse(content=did_document)
```

The DID document is assembled as a plain dict by
[`DIDAgentExtension.get_did_document`](../../bindu/extensions/did/did_agent_extension.py)
— not a pydantic model. Why? Because the W3C DID spec requires the
`@context` key, which is not a valid Python identifier and doesn't
round-trip cleanly through a plain TypedDict attribute name. The
path of least resistance was to build it as a dict with literal key
strings.

Consequence: the wire-format contract that `bindu/common/protocol/types.py`
enforces everywhere else (`alias_generator=to_camel`,
`by_alias=True`) had no hook into this path. The endpoint was
*accidentally* correct today because the human who wrote
`get_did_document()` happened to type `publicKeyBase58` camelCase.
One future typo, one PR that adds a new field the Python way, and
the contract silently breaks.

## Fix

Added a small recursive normalizer at
[`bindu/server/endpoints/did_endpoints.py`](../../bindu/server/endpoints/did_endpoints.py)
that converts snake_case dict keys to camelCase on the way out,
preserving `@context` and already-camelCase keys unchanged. The
endpoint now returns
`JSONResponse(content=_normalize_did_document_keys(did_document))`.

Rules the normalizer applies:

- Keys starting with `@` pass through (JSON-LD convention,
  including `@context`, `@id`, `@type`).
- Keys without an underscore pass through (they're already single
  words or camelCase).
- Keys containing an underscore go through
  `pydantic.alias_generators.to_camel` — the exact transform used
  by the rest of the A2A type system.

Tests in [`tests/unit/server/endpoints/test_did_endpoints.py`](../../tests/unit/server/endpoints/test_did_endpoints.py)
— 9 cases:

- Today's W3C-correct document is returned byte-for-byte unchanged
  (no over-eager transforms).
- `@context` preserved.
- `snake_case` → `camelCase`.
- `alreadyCamelCase` passes through untouched (no double-transform).
- Nested dicts and lists are walked recursively.
- Realistic future document with a mix of W3C + Bindu-specific
  keys produces a fully camelCase output.
- Scalars, None, True, empty containers all round-trip safely.

No behavioral change observable from current clients; future
extensions are safe by construction.

## Why the tests didn't catch it

There were no tests for `did_endpoints.py` at all. The endpoint was
exercised in practice only by happy-path discovery calls, which
read the current W3C-correct document and were satisfied. A bug
that only manifests when someone *adds a field* can't be caught by
happy-path tests — you need a contract test asserting the shape of
the output regardless of what the data source chooses to emit.

The new tests are exactly that contract. They include a "realistic
future document" case that simulates a downstream change to
`get_did_document()` — if someone adds a snake_case field, the
existing test catches it before it ships.

## Class of bug — where else to watch

The general shape: **a JSON-producing endpoint that bypasses the
project's central serialization layer because its type is awkward
to express as a pydantic model**.

Places to audit for the same pattern:

- Any endpoint using `JSONResponse(content=<raw dict>)` where the
  dict isn't validated through pydantic. Grep:
  `grep -rn 'JSONResponse(content=' bindu/server/endpoints/`.
  Today that pattern appears a few places worth re-checking.
- Any extension's `get_*_document()` / `to_dict()` helper that
  returns a manually-assembled dict intended for the wire. The DID
  extension is one; check skills, negotiation, and x402 extensions
  for siblings.
- Error-response builders. Many error shapes are handwritten dicts;
  `jsonrpc_error` in `bindu/server/endpoints/utils.py` is the
  canonical path but not every error site goes through it.

The deeper lesson: **if a type is awkward to express as a pydantic
model, add the normalizer that bridges raw dicts into the same
wire-format contract — don't let the raw dict out un-normalized.**
A five-line helper beats a future compatibility break.

## Follow-ups

- One latent concern: the W3C DID spec defines ``keyAgreement``,
  ``assertionMethod``, ``capabilityInvocation``, and similar blocks
  as sibling arrays of ``authentication``. These are already
  camelCase in the spec and would pass through unchanged today.
  But if a future Bindu extension adds a private field for
  internal routing (e.g. ``service_endpoint`` for peer discovery),
  the normalizer will emit ``serviceEndpoint``. That's the correct
  output for A2A peers, but not necessarily what the DID extension
  author intended. If that tension arises, consider namespacing
  Bindu extensions under a single ``binduMeta`` block rather than
  flattening into the top-level document.
