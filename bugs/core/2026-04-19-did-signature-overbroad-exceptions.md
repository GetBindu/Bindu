---
id: 2026-04-19-did-signature-overbroad-exceptions
title: verify_signature caught every exception and made real bugs look like bad signatures
severity: low
status: fixed
found: 2026-04-18
fixed: 2026-04-19
area: bindu/utils/did
commit: (this PR)
pr:
issue:
---

## Symptom

`bindu.utils.did.signature.verify_signature` is the crypto core of
the DID authentication layer. It's called from the Hydra middleware
for every DID-authenticated request. Operators reading server logs
saw exactly one message for every failure mode:

```
WARNING: Invalid DID signature for did:bindu:alice:...
DEBUG:   Signature verification failed: <whatever>
```

"Invalid DID signature" meant *all* of the following:

- Genuine crypto mismatch (attacker tampering / wrong key)
- Caller sent malformed base58
- Caller sent a public key of wrong length
- AttributeError in our own code because we mis-typed a method name
- ImportError because a dependency went missing
- Any other Python exception that happened to fire inside the try
  block

Operators investigating a failed request couldn't tell whether
they were looking at an attack, a misconfigured client, or a bug
on the server side. Everything collapsed to one message.

## Root cause

At [`bindu/utils/did/signature.py`](../../bindu/utils/did/signature.py)
pre-fix:

```python
try:
    public_key_bytes = base58.b58decode(public_key)
    signature_bytes = base58.b58decode(signature)
    verify_key = VerifyKey(public_key_bytes)
    verify_key.verify(payload_str.encode("utf-8"), signature_bytes)
    is_valid = True
except (BadSignatureError, ValueError, TypeError, Exception) as e:
    logger.debug(f"Signature verification failed: {e}")
    is_valid = False
```

The trailing `Exception` in the tuple does the damage. `Exception`
is the base class of almost every runtime error in Python —
including `AttributeError`, `ImportError`, `KeyError`,
`ZeroDivisionError`, and every random third-party exception. The
try block wrapped four quite different operations (decode, decode,
construct, verify) and the except treated them all as "signature
failure."

Why did this ship? The author clearly intended the tuple to be a
belt-and-braces catch-all: "the narrow exceptions we expect, plus
anything weird." But in Python that's an anti-pattern — catching
the base class after the narrow classes makes the narrow ones
redundant, and the catch-all swallows bugs. The right shape is
narrow catches only, with distinct try blocks per concern.

Second issue: because the inner `except` swallowed everything, the
*outer* `except (ImportError, UnicodeEncodeError, ValueError,
TypeError)` that wraps the whole function was effectively dead
code for the decode/verify path. It never saw any of those
exceptions.

## Fix

Three narrow try blocks, each for a single failure mode, with
distinct log reasons and no catch-all:

```python
# 1. Replay guard (no try — a comparison can't throw)
if abs(current_time - timestamp) > max_age_seconds:
    logger.warning("… (timestamp_out_of_window) …")
    return False

# 2. Decode step — base58 / key construction
try:
    public_key_bytes = base58.b58decode(public_key)
    signature_bytes = base58.b58decode(signature)
    verify_key = VerifyKey(public_key_bytes)
except (ValueError, TypeError) as e:
    logger.warning(f"… (malformed_input) … {e}")
    return False

# 3. Verify step — the only place BadSignatureError can come from
try:
    verify_key.verify(payload_str.encode("utf-8"), signature_bytes)
except BadSignatureError:
    logger.warning("… (crypto_mismatch) …")
    return False

return True
```

The outer catch-all was removed — it only ever fired when the
function was used incorrectly. Bugs of that shape now propagate to
the caller, which is what we want.

Three distinct reason codes in the logs:

- `timestamp_out_of_window` — replay-window reject
- `malformed_input` — base58 decode failure or wrong key length
- `crypto_mismatch` — genuine signature math failure

Operators can now grep for the specific failure mode, and a bug
on our side (AttributeError, missing import, etc.) raises loudly
instead of silently returning `False`.

Tests: [`tests/unit/utils/did/test_signature.py`](../../tests/unit/utils/did/test_signature.py)
— 9 cases:

- Happy path: valid signature accepted.
- Six legitimate reject cases, one per failure mode (timestamp,
  malformed signature, malformed public key, wrong-length key,
  valid-base58-but-wrong-signature, body tampering).
- **Two regression guards**: a patched `VerifyKey.verify` raising
  `RuntimeError` and a patched `create_signature_payload` raising
  `AttributeError`. Pre-fix these would have been swallowed and
  silently returned `False`. Post-fix they propagate — if the
  broad-except bug ever comes back, these tests fail loudly.

All 809 unit tests pass.

## Why the tests didn't catch it

There were no direct unit tests for `verify_signature` at all.
Tests that exercised it transitively (the Hydra middleware tests
at `tests/unit/server/middleware/test_hydra_did_signature.py`) all
used happy-path crypto — they passed real keys and real
signatures. The interesting cases — malformed input, bugs inside
the try block — were never exercised.

The new regression tests do the one thing the old suite never
did: inject unexpected exceptions mid-verification and assert they
propagate. Any future change that reintroduces a broad `except`
will fail those tests.

## Class of bug — where else to watch

The general shape: **a try-except tuple that mixes narrow expected
exceptions with a catch-all base class**. In Python, the canonical
form of this anti-pattern is:

```python
except (SomeSpecific, OtherSpecific, Exception) as e:
```

The `Exception` at the end silently subsumes the specific ones and
catches literally every bug. Grep target: `except \(.*Exception\)`
(tuple that ends in `Exception`).

Places to audit for the same shape:

- Any crypto / signing / verifying code added in the future. The
  same footgun is extremely tempting when dealing with library
  code that can raise many exception types.
- Webhook delivery paths (notifications). Easy to reach for a
  broad catch when "any network failure counts as delivery
  failure."
- Middleware in general — a catch-all that maps every exception to
  a generic 500 is an observability disaster.

Also worth an audit: any `try/except` where the corresponding log
line says *only* "failed" without naming the specific reason.
Those are the paths where triage goes to die.

## Follow-ups

- Apply the same pattern discipline to the x402 payment middleware
  — it has several broad `except Exception` blocks (see
  `bugs/known-issues.md` entries `x402-*`) that swallow crypto /
  RPC errors the same way.
- The Hydra middleware tests (`test_hydra_did_signature.py`) could
  be extended with the same "inject unexpected exception, assert
  it propagates" pattern for the middleware layer, not just
  `verify_signature` itself.
