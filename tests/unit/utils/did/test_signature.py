"""Tests for ``bindu.utils.did.signature.verify_signature``.

The key property these tests guard: **unexpected exceptions
propagate, they are not swallowed as "bad signature."** Pre-fix the
function caught ``(BadSignatureError, ValueError, TypeError, Exception)``
and returned ``False`` for all of them, which made every bug look
identical in the telemetry to a legitimate cryptographic failure.

The fix splits the decode and verify steps and catches only the
narrow exceptions each step legitimately emits. Bugs elsewhere
propagate.

See ``bugs/core/2026-04-19-did-signature-overbroad-exceptions.md``
for context.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import base58
import pytest
from nacl.signing import SigningKey

from bindu.utils.did.signature import sign_request, verify_signature


# ---------------------------------------------------------------------------
# Test fixtures — a stable signing/verification keypair
# ---------------------------------------------------------------------------


SEED = b"\x00" * 32  # deterministic test seed; not a real secret
_SK = SigningKey(SEED)
_PUBLIC_KEY_B58 = base58.b58encode(bytes(_SK.verify_key)).decode()
DID = "did:bindu:test"


class _FakeDidExtension:
    """Minimal stand-in for DIDAgentExtension — sign_request() only
    calls `.sign_message(text) -> base58 str`."""

    def sign_message(self, text: str) -> str:
        return base58.b58encode(_SK.sign(text.encode("utf-8")).signature).decode()


def _sign_headers(body):
    return sign_request(body, DID, _FakeDidExtension())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestVerifySignatureHappyPath:
    def test_valid_signature_accepted(self):
        body = b'{"method": "message/send", "id": "1"}'
        h = _sign_headers(body)
        assert (
            verify_signature(
                body=body,
                signature=h["X-DID-Signature"],
                did=DID,
                timestamp=int(h["X-DID-Timestamp"]),
                public_key=_PUBLIC_KEY_B58,
            )
            is True
        )


# ---------------------------------------------------------------------------
# Legitimate reject paths — each returns False with a distinct reason
# ---------------------------------------------------------------------------


class TestVerifySignatureLegitimateRejects:
    """Three genuine failure modes; each should log a distinct reason
    code so operators can tell them apart in triage."""

    def test_timestamp_too_old_rejected(self):
        body = b'{"x": 1}'
        h = _sign_headers(body)
        stale_ts = int(time.time()) - 3600  # 1 hour ago
        ok = verify_signature(
            body=body,
            signature=h["X-DID-Signature"],
            did=DID,
            timestamp=stale_ts,
            public_key=_PUBLIC_KEY_B58,
        )
        assert ok is False

    def test_malformed_base58_signature_rejected(self):
        body = b'{"x": 1}'
        h = _sign_headers(body)
        # "!!!" is not valid base58 — decode branch, not an unhandled raise.
        ok = verify_signature(
            body=body,
            signature="!!!not-base58!!!",
            did=DID,
            timestamp=int(h["X-DID-Timestamp"]),
            public_key=_PUBLIC_KEY_B58,
        )
        assert ok is False

    def test_malformed_base58_public_key_rejected(self):
        body = b'{"x": 1}'
        h = _sign_headers(body)
        ok = verify_signature(
            body=body,
            signature=h["X-DID-Signature"],
            did=DID,
            timestamp=int(h["X-DID-Timestamp"]),
            public_key="!!!not-base58!!!",
        )
        assert ok is False

    def test_wrong_length_public_key_rejected(self):
        """base58-decodes cleanly but is the wrong length for Ed25519
        — VerifyKey constructor raises ValueError. Same decode branch
        should catch it, not let it escape."""
        body = b'{"x": 1}'
        h = _sign_headers(body)
        too_short = base58.b58encode(b"\x00" * 10).decode()
        ok = verify_signature(
            body=body,
            signature=h["X-DID-Signature"],
            did=DID,
            timestamp=int(h["X-DID-Timestamp"]),
            public_key=too_short,
        )
        assert ok is False

    def test_valid_base58_but_wrong_signature_rejected(self):
        """Signature is well-formed base58 of the right length, but
        doesn't match the message. BadSignatureError — distinct branch
        from the malformed-input one."""
        body = b'{"x": 1}'
        fake_sig = base58.b58encode(b"\x00" * 64).decode()
        ok = verify_signature(
            body=body,
            signature=fake_sig,
            did=DID,
            timestamp=int(time.time()),
            public_key=_PUBLIC_KEY_B58,
        )
        assert ok is False

    def test_body_tamper_rejected(self):
        """Sign a body, then pass a different body to verify. Valid
        base58, right-length key, math fails."""
        h = _sign_headers(b'{"x": 1}')
        ok = verify_signature(
            body=b'{"x": 2}',  # tampered
            signature=h["X-DID-Signature"],
            did=DID,
            timestamp=int(h["X-DID-Timestamp"]),
            public_key=_PUBLIC_KEY_B58,
        )
        assert ok is False


# ---------------------------------------------------------------------------
# The core regression test for this fix: unexpected exceptions must propagate
# ---------------------------------------------------------------------------


class TestVerifySignatureUnexpectedExceptionsPropagate:
    """Pre-fix behavior: ``except (BadSignatureError, ValueError,
    TypeError, Exception)`` — every exception type returned False. A
    real bug (AttributeError, RuntimeError, ImportError, ...) looked
    identical to a genuine signature failure in the logs, hiding the
    problem.

    Post-fix: only BadSignatureError / ValueError / TypeError are
    caught on the specific narrow lines they can legitimately come
    from. Anything else propagates to the caller.

    These tests inject an unexpected exception into the crypto call
    and assert it raises, NOT that it returns False.
    """

    def test_runtime_error_in_verify_step_propagates(self):
        body = b'{"x": 1}'
        h = _sign_headers(body)

        # Patch VerifyKey.verify to raise an unexpected error. If the
        # broad-except bug returned, this would return False silently.
        with patch(
            "nacl.signing.VerifyKey.verify",
            side_effect=RuntimeError("kernel panic"),
        ):
            with pytest.raises(RuntimeError, match="kernel panic"):
                verify_signature(
                    body=body,
                    signature=h["X-DID-Signature"],
                    did=DID,
                    timestamp=int(h["X-DID-Timestamp"]),
                    public_key=_PUBLIC_KEY_B58,
                )

    def test_attribute_error_in_payload_build_propagates(self):
        """If create_signature_payload ever regresses and raises an
        AttributeError, it must surface — not be silently mapped to
        'invalid signature.'"""
        body = b'{"x": 1}'
        h = _sign_headers(body)

        with patch(
            "bindu.utils.did.signature.create_signature_payload",
            side_effect=AttributeError("internal bug"),
        ):
            with pytest.raises(AttributeError, match="internal bug"):
                verify_signature(
                    body=body,
                    signature=h["X-DID-Signature"],
                    did=DID,
                    timestamp=int(h["X-DID-Timestamp"]),
                    public_key=_PUBLIC_KEY_B58,
                )
