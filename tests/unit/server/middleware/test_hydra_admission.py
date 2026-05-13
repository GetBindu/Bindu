"""Unit tests for HydraMiddleware's DID admission control.

Covers the `_is_did_admitted` helper that gates which DIDs may reach
handlers after Hydra introspection + signature verification have passed.
See the resolved bug `did-admission-control-missing` in
`bugs/known-issues.md` for context.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bindu.server.middleware.auth.hydra import HydraMiddleware


ALICE_DID = "did:bindu:alice"
EVIL_DID = "did:bindu:evil:scammer"


def _middleware(monkeypatch, *, allowed_dids):
    """Build a HydraMiddleware with the given allowlist.

    `_initialize_provider` is neutralized so no Hydra HTTP connection
    is attempted; hydra_client is replaced with an AsyncMock.
    """
    monkeypatch.setattr(HydraMiddleware, "_initialize_provider", lambda self: None)

    config = Mock()
    config.public_endpoints = []
    config.allowed_dids = allowed_dids

    mw = HydraMiddleware(app=Mock(), auth_config=config)
    mw.hydra_client = AsyncMock()
    return mw


class TestDidAdmission:
    """`_is_did_admitted` decides whether an authenticated DID may proceed."""

    def test_allowlist_none_admits_any_did(self, monkeypatch):
        """Default behavior — no allowlist configured, every authenticated
        DID is admitted (current pre-fix behavior preserved)."""
        mw = _middleware(monkeypatch, allowed_dids=None)
        assert mw._is_did_admitted(ALICE_DID) is True
        assert mw._is_did_admitted(EVIL_DID) is True
        # Non-DID client_id also passes when no allowlist is configured.
        assert mw._is_did_admitted("some-legacy-client") is True

    def test_listed_did_is_admitted(self, monkeypatch):
        mw = _middleware(monkeypatch, allowed_dids=[ALICE_DID])
        assert mw._is_did_admitted(ALICE_DID) is True

    def test_unlisted_did_is_rejected(self, monkeypatch):
        """Regression: with an allowlist configured, a Hydra-registered DID
        that is not on the list must be rejected. This is the core fix for
        `did-admission-control-missing`."""
        mw = _middleware(monkeypatch, allowed_dids=[ALICE_DID])
        assert mw._is_did_admitted(EVIL_DID) is False

    def test_empty_allowlist_rejects_everyone(self, monkeypatch):
        """An empty list is the explicit deny-all posture — distinct from
        None, which means 'no admission filter'."""
        mw = _middleware(monkeypatch, allowed_dids=[])
        assert mw._is_did_admitted(ALICE_DID) is False
        assert mw._is_did_admitted(EVIL_DID) is False

    def test_none_client_did_rejected_when_allowlist_configured(self, monkeypatch):
        """A missing client_id cannot be in any non-None allowlist."""
        mw = _middleware(monkeypatch, allowed_dids=[ALICE_DID])
        assert mw._is_did_admitted(None) is False
        assert mw._is_did_admitted("") is False

    def test_config_without_allowed_dids_attribute_admits(self, monkeypatch):
        """Backwards compatibility: pre-existing AuthSettings objects that
        lack the new field must default to admit-all, not crash."""
        monkeypatch.setattr(
            HydraMiddleware, "_initialize_provider", lambda self: None
        )
        config = Mock(spec=["public_endpoints"])
        config.public_endpoints = []
        mw = HydraMiddleware(app=Mock(), auth_config=config)
        mw.hydra_client = AsyncMock()

        assert mw._is_did_admitted(ALICE_DID) is True


class TestAdmissionFlow:
    """Light integration check: the rejection path returns 403 and does
    not forward to the wrapped app."""

    @pytest.mark.asyncio
    async def test_rejected_request_returns_403_and_does_not_forward(
        self, monkeypatch
    ):
        mw = _middleware(monkeypatch, allowed_dids=[ALICE_DID])

        # The wrapped app must not be called when admission is denied.
        app_mock = AsyncMock()
        mw.app = app_mock

        # Patch the heavy lifting: token validation returns a payload for
        # EVIL_DID; signature verification is bypassed (returns True).
        async def fake_validate_token(token):
            return {"sub": "evil", "client_id": EVIL_DID, "active": True}

        async def fake_verify_did_signature_asgi(receive, client_did, headers):
            return True, {"did_verified": True}, receive

        monkeypatch.setattr(mw, "_validate_token", fake_validate_token)
        monkeypatch.setattr(
            mw, "_verify_did_signature_asgi", fake_verify_did_signature_asgi
        )

        sent_messages: list[dict] = []

        async def send(message):
            sent_messages.append(message)

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [
                (b"authorization", b"Bearer faketoken"),
                (b"x-did-signature", b"sig"),
            ],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "root_path": "",
        }

        await mw(scope, receive, send)

        # Wrapped app was not called.
        app_mock.assert_not_awaited()
        # A 403 response was sent.
        start_messages = [m for m in sent_messages if m.get("type") == "http.response.start"]
        assert start_messages, "no http.response.start emitted"
        assert start_messages[0]["status"] == 403
