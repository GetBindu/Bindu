"""Tests for ScopeBlind middleware."""

from __future__ import annotations

import json

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu.extensions.scopeblind import ScopeBlindExtension
from bindu.server.middleware.scopeblind import ScopeBlindMiddleware


def _write_policy(policy_dir: Path, content: str) -> None:
    """Write a test Cedar policy."""
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "policy.cedar").write_text(content, encoding="utf-8")


def _build_request() -> Request:
    """Build a test HTTP request."""
    body = json.dumps({"jsonrpc": "2.0", "id": "1", "method": "message/send"}).encode(
        "utf-8"
    )

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "raw_path": b"/",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }
    request = Request(scope, receive)
    request.state.authenticated = True
    request.state.user = {
        "sub": "alice",
        "is_m2m": False,
        "scope": ["agent:invoke"],
        "client_id": "client-1",
    }
    return request


class TestScopeBlindMiddleware:
    """Test ScopeBlind middleware behavior."""

    @pytest.mark.asyncio
    async def test_allow_calls_next(self, tmp_path: Path):
        """Allowed requests should continue through the middleware chain."""
        policy_dir = tmp_path / "policies"
        _write_policy(
            policy_dir,
            'permit(principal, action == Action::"message/send", resource);',
        )
        extension = ScopeBlindExtension(
            mode="enforce",
            cedar_policies=str(policy_dir),
            key_dir=tmp_path / "keys",
        )
        middleware = ScopeBlindMiddleware(app=Mock(), scopeblind_ext=extension)
        request = _build_request()
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()
        assert request.state.scopeblind_context["decision"] == "Allow"

    @pytest.mark.asyncio
    async def test_enforce_deny_blocks_execution(self, tmp_path: Path):
        """Denied requests in enforce mode should return 403 and skip execution."""
        policy_dir = tmp_path / "policies"
        _write_policy(
            policy_dir,
            'forbid(principal, action == Action::"message/send", resource);',
        )
        extension = ScopeBlindExtension(
            mode="enforce",
            cedar_policies=str(policy_dir),
            key_dir=tmp_path / "keys",
        )
        middleware = ScopeBlindMiddleware(app=Mock(), scopeblind_ext=extension)
        request = _build_request()
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 403
        call_next.assert_not_called()
        assert request.state.scopeblind_context["decision"] == "Deny"

    @pytest.mark.asyncio
    async def test_shadow_deny_allows_execution(self, tmp_path: Path):
        """Denied requests in shadow mode should continue and preserve denial context."""
        policy_dir = tmp_path / "policies"
        _write_policy(
            policy_dir,
            'forbid(principal, action == Action::"message/send", resource);',
        )
        extension = ScopeBlindExtension(
            mode="shadow",
            cedar_policies=str(policy_dir),
            key_dir=tmp_path / "keys",
        )
        middleware = ScopeBlindMiddleware(app=Mock(), scopeblind_ext=extension)
        request = _build_request()
        call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_called_once()
        assert request.state.scopeblind_context["decision"] == "Deny"
