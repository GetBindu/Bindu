"""Unit tests for ``HydraMiddleware`` token introspection cache.

Covers the revocation-lag fix — see
``bugs/core/2026-04-26-hydra-token-cache-revocation-lag.md``. The two
guarantees we want pinned down:

1. Tokens carrying a sensitive scope are never cached. The next request
   re-introspects, so a Hydra-side revocation takes effect immediately.
2. ``invalidate_token_cache`` (and the wrapping ``revoke_token``) drops
   the cached entry on the local instance.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock

import pytest

from bindu.server.middleware.auth.hydra import (
    DEFAULT_SENSITIVE_SCOPES,
    HydraMiddleware,
)


def _make_middleware(monkeypatch, *, cache_ttl: int = 300, sensitive_scopes=None):
    """Build a HydraMiddleware whose hydra_client is a mock.

    ``_initialize_provider`` is neutralized so no HTTP connection is
    attempted during construction. ``hydra_client`` is replaced with an
    ``AsyncMock``.
    """
    monkeypatch.setattr(HydraMiddleware, "_initialize_provider", lambda self: None)

    config = Mock()
    config.public_endpoints = []
    config.cache_ttl = cache_ttl
    if sensitive_scopes is not None:
        config.sensitive_scopes = sensitive_scopes
    else:
        # Fall back to the module default when the test does not
        # configure scopes explicitly.
        del config.sensitive_scopes

    mw = HydraMiddleware(app=Mock(), auth_config=config)
    mw.hydra_client = AsyncMock()
    return mw


def _active_introspection(scope: str = "agent:read", *, exp_in: int = 3600):
    return {
        "active": True,
        "sub": "user-1",
        "exp": int(time.time()) + exp_in,
        "scope": scope,
    }


class TestSensitiveScopesBypassCache:
    """Tokens with sensitive scopes must not be cached."""

    @pytest.mark.asyncio
    async def test_admin_scope_token_is_not_cached(self, monkeypatch):
        mw = _make_middleware(monkeypatch)
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="admin agent:read"
        )

        await mw._validate_token("admin-token")
        await mw._validate_token("admin-token")

        # Both calls must hit Hydra — no caching for sensitive scopes.
        assert mw.hydra_client.introspect_token.await_count == 2
        assert mw._introspection_cache == {}

    @pytest.mark.asyncio
    async def test_payment_capture_scope_is_not_cached(self, monkeypatch):
        mw = _make_middleware(monkeypatch)
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="payment:capture"
        )

        await mw._validate_token("pay-token")
        await mw._validate_token("pay-token")

        assert mw.hydra_client.introspect_token.await_count == 2
        assert mw._introspection_cache == {}

    @pytest.mark.asyncio
    async def test_non_sensitive_scope_is_cached(self, monkeypatch):
        mw = _make_middleware(monkeypatch)
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="agent:read"
        )

        await mw._validate_token("read-token")
        await mw._validate_token("read-token")

        # Second call served from cache.
        assert mw.hydra_client.introspect_token.await_count == 1
        assert len(mw._introspection_cache) == 1

    @pytest.mark.asyncio
    async def test_custom_sensitive_scopes_override_defaults(self, monkeypatch):
        # An operator narrows the sensitive-scope set to only their custom
        # scope; previously-default scopes (e.g. "admin") become cacheable.
        mw = _make_middleware(monkeypatch, sensitive_scopes=["my:secret"])
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="admin"
        )

        await mw._validate_token("admin-token")
        await mw._validate_token("admin-token")

        assert mw.hydra_client.introspect_token.await_count == 1

    @pytest.mark.asyncio
    async def test_empty_sensitive_scopes_caches_everything(self, monkeypatch):
        mw = _make_middleware(monkeypatch, sensitive_scopes=[])
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="admin payment:capture"
        )

        await mw._validate_token("token")
        await mw._validate_token("token")

        assert mw.hydra_client.introspect_token.await_count == 1


class TestRevocationInvalidatesCache:
    """``revoke_token`` and ``invalidate_token_cache`` clear the entry."""

    @pytest.mark.asyncio
    async def test_invalidate_token_cache_drops_entry(self, monkeypatch):
        mw = _make_middleware(monkeypatch)
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="agent:read"
        )

        # Prime the cache.
        await mw._validate_token("tok")
        assert len(mw._introspection_cache) == 1

        # Invalidate — next call must re-introspect.
        assert mw.invalidate_token_cache("tok") is True
        assert mw._introspection_cache == {}

        await mw._validate_token("tok")
        assert mw.hydra_client.introspect_token.await_count == 2

    def test_invalidate_token_cache_returns_false_if_absent(self, monkeypatch):
        mw = _make_middleware(monkeypatch)
        assert mw.invalidate_token_cache("never-cached") is False

    @pytest.mark.asyncio
    async def test_revoke_token_invalidates_locally_after_hydra_call(self, monkeypatch):
        mw = _make_middleware(monkeypatch)
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="agent:read"
        )
        mw.hydra_client.revoke_token.return_value = True

        # Prime the cache, then revoke.
        await mw._validate_token("tok")
        assert len(mw._introspection_cache) == 1

        revoked = await mw.revoke_token("tok")

        assert revoked is True
        mw.hydra_client.revoke_token.assert_awaited_once_with("tok")
        assert mw._introspection_cache == {}

    @pytest.mark.asyncio
    async def test_revoke_token_invalidates_even_if_hydra_returns_false(
        self, monkeypatch
    ):
        # Hydra returns 4xx (e.g. token already gone) — we still want the
        # local cache cleared so the local view matches Hydra's.
        mw = _make_middleware(monkeypatch)
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="agent:read"
        )
        mw.hydra_client.revoke_token.return_value = False

        await mw._validate_token("tok")
        revoked = await mw.revoke_token("tok")

        assert revoked is False
        assert mw._introspection_cache == {}


class TestCacheTtlConfig:
    """``cache_ttl`` is read from auth config, not hardcoded."""

    @pytest.mark.asyncio
    async def test_short_ttl_expires_cache_entry(self, monkeypatch):
        mw = _make_middleware(monkeypatch, cache_ttl=1)
        # Token exp far in the future, so cache TTL is the binding limit.
        mw.hydra_client.introspect_token.return_value = _active_introspection(
            scope="agent:read", exp_in=3600
        )

        await mw._validate_token("tok")
        # Force the cached entry past its TTL.
        cached = next(iter(mw._introspection_cache.values()))
        cached["expires_at"] = time.time() - 1

        await mw._validate_token("tok")
        assert mw.hydra_client.introspect_token.await_count == 2

    def test_default_sensitive_scopes_match_module_constant(self, monkeypatch):
        mw = _make_middleware(monkeypatch, sensitive_scopes=None)
        assert mw._sensitive_scopes == DEFAULT_SENSITIVE_SCOPES
