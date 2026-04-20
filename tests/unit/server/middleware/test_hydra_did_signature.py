"""Unit tests for ``HydraMiddleware._verify_did_signature_asgi``.

Covers both the two fail-open paths that used to accept unsigned requests
from DID clients, and the regression surface around them. See
``bugs/2026-04-18-did-signature-fail-open.md`` for context.

Each test constructs a minimal HydraMiddleware with ``_initialize_provider``
bypassed (so no real Hydra connection is attempted) and the ``hydra_client``
replaced with an ``AsyncMock``. The DID crypto subroutine ``verify_signature``
is patched at its import site inside ``hydra`` when a test cares about the
crypto result.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bindu.server.middleware.auth.hydra import (
    MAX_BODY_SIZE_BYTES,
    HydraMiddleware,
)


ALICE_DID = "did:bindu:alice"
FAKE_PK = "base58encodedpublickey"


@pytest.fixture
def middleware(monkeypatch):
    """Build a HydraMiddleware whose hydra_client is a mock.

    _initialize_provider is neutralized so no HTTP connection is attempted
    during construction. The test sets self.hydra_client directly afterwards.
    """
    monkeypatch.setattr(HydraMiddleware, "_initialize_provider", lambda self: None)

    config = Mock()
    config.public_endpoints = []

    mw = HydraMiddleware(app=Mock(), auth_config=config)
    mw.hydra_client = AsyncMock()
    return mw


async def _empty_receive():
    """ASGI receive that yields one empty body chunk and terminates."""
    return {"type": "http.request", "body": b"", "more_body": False}


def _signed_headers(did=ALICE_DID, body_len=0):
    return {
        "X-DID": did,
        "X-DID-Signature": "base58encodedsignature",
        "X-DID-Timestamp": "1713456000",
        "content-length": str(body_len),
    }


class TestDidSignatureFailClosed:
    """The two previously-fail-open paths now refuse the request."""

    @pytest.mark.asyncio
    async def test_missing_signature_headers_rejected(self, middleware):
        """No X-DID-Signature → must reject, not silently accept.

        This is the primary attack: a DID client omits the signature
        headers entirely and expects to slip through. Pre-fix, the
        function returned is_valid=True with reason="no_signature_headers"
        and the caller at hydra.py:274 let the request through.
        """
        is_valid, info, _ = await middleware._verify_did_signature_asgi(
            receive=_empty_receive, client_did=ALICE_DID, headers={}
        )
        assert is_valid is False
        assert info["did_verified"] is False
        assert info["reason"] == "missing_signature_headers"
        # hydra_client must not be consulted at all on this path
        middleware.hydra_client.get_public_key_from_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_public_key_rejected(self, middleware):
        """Hydra has no public_key in the DID client's metadata → reject.

        Pre-fix, this path returned is_valid=True with
        reason="no_public_key" — allowing anyone who could register a
        DID client without a public key in metadata to bypass signing.
        """
        middleware.hydra_client.get_public_key_from_client.return_value = None

        is_valid, info, _ = await middleware._verify_did_signature_asgi(
            receive=_empty_receive,
            client_did=ALICE_DID,
            headers=_signed_headers(),
        )
        assert is_valid is False
        assert info["did_verified"] is False
        assert info["reason"] == "public_key_unavailable"

    @pytest.mark.asyncio
    async def test_empty_string_public_key_rejected(self, middleware):
        """Empty-string public_key (falsy) is handled the same as missing."""
        middleware.hydra_client.get_public_key_from_client.return_value = ""

        is_valid, info, _ = await middleware._verify_did_signature_asgi(
            receive=_empty_receive,
            client_did=ALICE_DID,
            headers=_signed_headers(),
        )
        assert is_valid is False
        assert info["reason"] == "public_key_unavailable"


class TestDidSignatureRegression:
    """Pre-existing behavior that must keep working after the fix."""

    @pytest.mark.asyncio
    async def test_did_header_mismatch_rejected(self, middleware):
        """Caller authenticated as Alice but signed as Bob → reject.

        The signature claims a different DID than the token's client_id.
        The mismatch check must run BEFORE the hydra key lookup so the
        wrong-DID case isn't masked by a subsequent failure.
        """
        is_valid, info, _ = await middleware._verify_did_signature_asgi(
            receive=_empty_receive,
            client_did=ALICE_DID,
            headers=_signed_headers(did="did:bindu:bob"),
        )
        assert is_valid is False
        assert info["reason"] == "did_mismatch"
        middleware.hydra_client.get_public_key_from_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_payload_too_large_rejected(self, middleware):
        """Bodies over MAX_BODY_SIZE_BYTES rejected before crypto runs."""
        middleware.hydra_client.get_public_key_from_client.return_value = FAKE_PK

        headers = _signed_headers(body_len=MAX_BODY_SIZE_BYTES + 1)

        is_valid, info, _ = await middleware._verify_did_signature_asgi(
            receive=_empty_receive, client_did=ALICE_DID, headers=headers
        )
        assert is_valid is False
        assert info["reason"] == "payload_too_large"

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self, middleware, monkeypatch):
        """Happy path — signature headers present, DID matches, pk
        resolved, crypto verify returns True."""
        middleware.hydra_client.get_public_key_from_client.return_value = FAKE_PK

        monkeypatch.setattr(
            "bindu.server.middleware.auth.hydra.verify_signature",
            lambda **kwargs: True,
        )

        # Simulate a small body coming through receive
        receive_calls = [
            {"type": "http.request", "body": b'{"hello":"world"}', "more_body": False}
        ]

        async def receive():
            return receive_calls.pop(0)

        is_valid, info, new_receive = await middleware._verify_did_signature_asgi(
            receive=receive,
            client_did=ALICE_DID,
            headers=_signed_headers(body_len=17),
        )
        assert is_valid is True
        assert info["did_verified"] is True
        assert info["reason"] is None
        assert info["did"] == ALICE_DID
        # The body must be replayable to the downstream app via new_receive
        replayed = await new_receive()
        assert replayed["body"] == b'{"hello":"world"}'

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, middleware, monkeypatch):
        """Signature headers present and well-formed but crypto fails."""
        middleware.hydra_client.get_public_key_from_client.return_value = FAKE_PK

        monkeypatch.setattr(
            "bindu.server.middleware.auth.hydra.verify_signature",
            lambda **kwargs: False,
        )

        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}

        is_valid, info, _ = await middleware._verify_did_signature_asgi(
            receive=receive,
            client_did=ALICE_DID,
            headers=_signed_headers(body_len=2),
        )
        assert is_valid is False
        assert info["reason"] == "invalid_signature"
