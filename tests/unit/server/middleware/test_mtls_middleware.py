"""Tests for the mTLS authentication middleware.

The middleware is pure ASGI, so tests construct minimal scope dicts and
fake send/receive callables — no Starlette TestClient, no live server.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Awaitable, Callable, Optional
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from bindu.server.middleware.auth.mtls import (
    SCOPE_KEY_PEER_CERT,
    SCOPE_KEY_PEER_DID,
    MTLSMiddleware,
)


# ---------------------------------------------------------------------------
# Cert fixtures
# ---------------------------------------------------------------------------


def _cert_pem(
    *, did_in_san: Optional[str] = None, did_in_cn: Optional[str] = None
) -> str:
    """Build a self-signed cert PEM with DID placement controlled by args."""
    pk = ec.generate_private_key(ec.SECP256R1())
    builder = (
        x509.CertificateBuilder()
        .subject_name(
            x509.Name(
                [x509.NameAttribute(NameOID.COMMON_NAME, did_in_cn or "anonymous")]
            )
        )
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .public_key(pk.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(hours=1))
    )
    if did_in_san:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(did_in_san)]),
            critical=False,
        )
    cert = builder.sign(pk, hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


# ---------------------------------------------------------------------------
# ASGI scaffolding
# ---------------------------------------------------------------------------


class _RecordingApp:
    """A minimal downstream ASGI app that just records what it sees."""

    def __init__(self) -> None:
        self.called = False
        self.last_scope: Optional[dict] = None

    async def __call__(self, scope, receive, send) -> None:
        self.called = True
        self.last_scope = scope


def _make_scope(*, path: str = "/", cert_chain: Optional[list[str]] = None) -> dict:
    scope: dict = {"type": "http", "path": path}
    if cert_chain is not None:
        scope["extensions"] = {"tls": {"client_cert_chain": cert_chain}}
    return scope


async def _collect_send() -> tuple[list[dict], Callable[[dict], Awaitable[None]]]:
    """Return (events_list, send_callable) pair."""
    events: list[dict] = []

    async def send(event):
        events.append(event)

    return events, send


def _mtls_config(**overrides) -> SimpleNamespace:
    """Build a settings-like object with the fields the middleware reads."""
    cfg = {
        "enabled": True,
        "mode": "hybrid",
        "require_client_cert": True,
    }
    cfg.update(overrides)
    return SimpleNamespace(**cfg)


def _install_middleware(
    config: SimpleNamespace, public_endpoints: list[str] | None = None
) -> tuple[MTLSMiddleware, _RecordingApp]:
    """Build the middleware while patching the Hydra public-endpoint list."""
    downstream = _RecordingApp()
    hydra_ns = SimpleNamespace(public_endpoints=public_endpoints or [])
    with patch("bindu.server.middleware.auth.mtls.app_settings") as settings:
        settings.hydra = hydra_ns
        middleware = MTLSMiddleware(app=downstream, mtls_config=config)
    return middleware, downstream


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPassThrough:
    @pytest.mark.asyncio
    async def test_websocket_scope_passes_through_untouched(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config())
        events, send = await _collect_send()
        scope: dict = {"type": "lifespan"}
        await middleware(scope, lambda: None, send)
        assert downstream.called
        assert events == []

    @pytest.mark.asyncio
    async def test_mode_off_passes_through(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config(mode="off"))
        events, send = await _collect_send()
        await middleware(_make_scope(), lambda: None, send)
        assert downstream.called
        assert events == []

    @pytest.mark.asyncio
    async def test_disabled_passes_through(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config(enabled=False))
        events, send = await _collect_send()
        await middleware(_make_scope(), lambda: None, send)
        assert downstream.called

    @pytest.mark.asyncio
    async def test_public_endpoint_bypasses_cert_requirement(self) -> None:
        middleware, downstream = _install_middleware(
            _mtls_config(),
            public_endpoints=["/health", "/.well-known/*"],
        )
        events, send = await _collect_send()
        await middleware(_make_scope(path="/health"), lambda: None, send)
        assert downstream.called
        assert events == []


class TestDIDExtraction:
    DID = "did:bindu:raahul:test:abc123"

    @pytest.mark.asyncio
    async def test_uri_san_did_is_injected(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config())
        events, send = await _collect_send()
        scope = _make_scope(cert_chain=[_cert_pem(did_in_san=self.DID)])
        await middleware(scope, lambda: None, send)
        assert downstream.called
        assert downstream.last_scope is not None
        assert downstream.last_scope[SCOPE_KEY_PEER_DID] == self.DID
        assert downstream.last_scope[SCOPE_KEY_PEER_CERT].startswith(
            "-----BEGIN CERTIFICATE-----"
        )

    @pytest.mark.asyncio
    async def test_cn_did_is_fallback(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config())
        events, send = await _collect_send()
        scope = _make_scope(cert_chain=[_cert_pem(did_in_cn=self.DID)])
        await middleware(scope, lambda: None, send)
        assert downstream.called
        assert downstream.last_scope is not None
        assert downstream.last_scope[SCOPE_KEY_PEER_DID] == self.DID


class TestRejection:
    @pytest.mark.asyncio
    async def test_missing_cert_with_require_client_cert_rejects(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config())
        events, send = await _collect_send()
        await middleware(_make_scope(), lambda: None, send)
        assert not downstream.called
        assert events[0]["type"] == "http.response.start"
        assert events[0]["status"] == 403

    @pytest.mark.asyncio
    async def test_missing_cert_with_soft_mode_passes_through(self) -> None:
        middleware, downstream = _install_middleware(
            _mtls_config(require_client_cert=False)
        )
        events, send = await _collect_send()
        await middleware(_make_scope(), lambda: None, send)
        assert downstream.called
        # No peer DID injected since there was no cert.
        assert downstream.last_scope is not None
        assert SCOPE_KEY_PEER_DID not in downstream.last_scope

    @pytest.mark.asyncio
    async def test_cert_without_did_rejects(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config())
        events, send = await _collect_send()
        # Cert has neither URI SAN nor a DID-shaped CN.
        scope = _make_scope(cert_chain=[_cert_pem()])
        await middleware(scope, lambda: None, send)
        assert not downstream.called
        assert events[0]["status"] == 403
        assert b"lacks an identifiable DID" in events[1]["body"]

    @pytest.mark.asyncio
    async def test_malformed_pem_rejected_as_missing_did(self) -> None:
        middleware, downstream = _install_middleware(_mtls_config())
        events, send = await _collect_send()
        scope = _make_scope(cert_chain=["not a pem"])
        await middleware(scope, lambda: None, send)
        assert not downstream.called
        assert events[0]["status"] == 403
