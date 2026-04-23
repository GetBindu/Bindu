---
id: 2026-04-18-did-signature-fail-open
title: DID signature middleware fails open when signature headers or public key are missing
severity: critical
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: bindu/server/middleware/auth
commit: (this PR)
pr:
issue:
---

## Symptom

The Hydra middleware in
[`bindu/server/middleware/auth/hydra.py`](../../bindu/server/middleware/auth/hydra.py)
ships a second-layer authentication check: for any OAuth caller whose
`client_id` starts with `did:`, every request body must be signed
with the caller's Ed25519 private key, and the middleware verifies
that signature against the public key registered in Hydra client
metadata. This layer exists so that if a bearer token is stolen, the
thief still cannot send arbitrary requests — they'd also need the
private key, which never leaves the DID holder's machine.

On the old code this layer was **optional in practice**. An attacker
holding a stolen bearer token for a DID client could bypass the
signature check entirely by one of two methods:

1. **Omit the signature headers.** Send a normal HTTP request with
   `Authorization: Bearer <stolen-token>` and no `X-DID-Signature`.
   The middleware noted "no signature headers present" and allowed
   the request to continue as if verification had succeeded.
2. **Register a DID client in Hydra without a `public_key` in
   metadata.** Send real-looking signature headers containing any
   bytes you like. The middleware tried to fetch the public key,
   got nothing back, and again allowed the request to continue as
   if verification had succeeded.

Both paths defeated the entire point of DID signing. An operator
would see "DID verification enabled" in their config and assume
tampering protection was in place, but the gate would swing open
for anyone who could either not sign or not register a key.

## Root cause

[`_verify_did_signature_asgi`](../../bindu/server/middleware/auth/hydra.py) at
`hydra.py:158-223` is only entered when the outer `__call__` gate
confirms the caller is a DID client (`client_did.startswith("did:")`
at `hydra.py:269`). At that point the contract is unambiguous:
*this caller must sign, otherwise they should not be using a
`did:*` client_id.*

But the function itself held a softer contract. Two branches
returned `is_valid=True` when the check couldn't be performed:

```python
# hydra.py:164-169 pre-fix
if not signature_data:
    return (
        True,
        {"did_verified": False, "reason": "no_signature_headers"},
        receive,
    )

# hydra.py:174-176 pre-fix
public_key = await self.hydra_client.get_public_key_from_client(client_did)
if not public_key:
    return True, {"did_verified": False, "reason": "no_public_key"}, receive
```

The calling site only consulted the first tuple element:

```python
# hydra.py:274
if not is_valid:
    return JSONResponse({"error": "Invalid DID signature"}, status_code=403)
```

The `did_verified: False` flag in the returned dict was intended
to be advisory telemetry, but nothing downstream checked it. From
the caller's perspective, `is_valid=True` meant "the request is
clean." The function was saying "I couldn't verify, but that's OK";
the caller was hearing "I verified, all good." Two incompatible
contracts in neighboring files, and the outer file wrote the final
decision.

This is the textbook **fail-open vs fail-closed** pattern. For
security checks fail-closed is the only safe default — a check
that silently allows a request when it cannot determine
authenticity provides no security at all, only the illusion of it.
Diagnostic "reason" metadata that isn't load-bearing is useful for
logs but does not substitute for a reject.

## Fix

Both branches now return `False` and log a clear operator-facing
warning explaining what the DID client did wrong or how to fix
their Hydra metadata:

- Missing `X-DID-Signature` → reason `"missing_signature_headers"`,
  `is_valid=False`. The caller reaches the `if not is_valid` gate
  at line 274 and receives a 403.
- Hydra has no `metadata.public_key` for this DID client → reason
  `"public_key_unavailable"`, `is_valid=False`, same 403.

Seven tests land alongside the fix in
[`tests/unit/server/middleware/test_hydra_did_signature.py`](../../tests/unit/server/middleware/test_hydra_did_signature.py):

- The two previously-fail-open paths (missing headers / missing
  public key) now return `is_valid=False`. Also covered: an
  empty-string public key is handled identically to a missing one.
- The pre-existing DID-mismatch branch (token claims one DID, the
  `X-DID` header claims another) still returns `is_valid=False`
  before the Hydra key lookup runs, so the check order remains
  correct.
- The payload-size guard still rejects oversize bodies before
  crypto runs.
- The happy path — all headers present, DID matches, Hydra returns
  a key, `verify_signature` returns True — still accepts, and the
  body remains replayable to the downstream app via the cached
  `receive` proxy.
- An otherwise-valid request where `verify_signature` returns
  False still rejects with reason `"invalid_signature"`.

No config flag was added. There is no "unsafe mode" that flips the
fail-open back on — if an operator has a DID client that can't
sign today, the correct remediation is to either (a) make the
client sign or (b) stop using a `did:` client_id for it.

## Why the tests didn't catch it

There were no unit tests for `_verify_did_signature_asgi` before
this fix. The middleware was exercised implicitly by integration
paths that always provided valid signatures, so every test case
was a happy-path test case. The interesting branches —
specifically the "can't verify" branches — had no coverage at
all. Fail-open bugs are particularly invisible to happy-path
tests because they only manifest when verification *fails* in a
novel way and the failure mode itself is what's broken.

The new test file covers the cross-product of signature-present
× public-key-present × crypto-result. Future changes to this
function will have a clear failure signal.

## Class of bug — where else to watch

Fail-open is a shape. In any security-relevant function that
returns a boolean "is the caller authorized / is the signature
valid / is the payment valid," ask: what is returned on the
exception path, on the "couldn't determine" path, on the "provider
is down" path? If the answer is anything other than "False, with
a reject," that's a variant of this bug.

In this codebase the places most likely to hold the same shape:

- [`bindu/server/middleware/x402/x402_middleware.py`](../../bindu/server/middleware/x402/x402_middleware.py)
  lines 213–215 still fail open on body-parse errors — tracked in
  `bugs/known-issues.md` as `x402-middleware-fails-open-on-body-parse`.
  Same pattern: the "can't parse" branch calls `await call_next(request)`
  instead of rejecting. Fixing this is independent from the DID fix
  but uses the same logic.
- [`bindu/utils/did/signature.py`](../../bindu/utils/did/signature.py)
  lines 114–126 (the underlying `verify_signature` helper) catch
  `Exception` broadly and return `False`. That is actually
  correctly fail-closed on the result, but the broad exception
  obscures which failure mode occurred — tracked as
  `did-signature-overbroad-exception-catch`.
- The Hydra introspection path at
  [`hydra.py:102-104`](../../bindu/server/middleware/auth/hydra.py)
  catches introspection errors and re-raises — correctly
  fail-closed. Worth a re-read when auditing.
- New middleware or signature-verification code added in the
  future: the rule is *return False when you can't check, never
  True with a "reason"*. Make the reject explicit at the decision
  point, not optional based on downstream consumption.

## Follow-ups

- The broad `except Exception` in `verify_signature` should be
  split into `(ValueError, TypeError)` for base58 decode errors
  and `BadSignatureError` for cryptographic failures, so logs
  distinguish "malformed input" from "wrong signature." Tracked
  as `did-signature-overbroad-exception-catch` in
  [`bugs/known-issues.md`](../known-issues.md).
- The Hydra token introspection cache still holds revoked tokens
  for up to 5 minutes (`hydra-token-cache-revocation-lag` in
  known-issues). Independent from this fix; still worth addressing.
