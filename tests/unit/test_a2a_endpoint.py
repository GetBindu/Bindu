"""Unit tests for A2A protocol endpoint focusing on authentication/authorization."""

import json
from types import SimpleNamespace
from typing import cast

import pytest

from bindu.server.endpoints.a2a_protocol import agent_run_endpoint
from bindu.server.applications import BinduApplication
from bindu.settings import app_settings


def _make_a2a_request(method: str, params: dict | None = None, headers: dict | None = None) -> object:
    """Create a minimal request object that mimics Starlette Request for A2A."""
    data = {"jsonrpc": "2.0", "id": "1", "method": method}
    if params is not None:
        data["params"] = params
    raw = json.dumps(data).encode()

    async def body():
        return raw

    request = SimpleNamespace(
        url=SimpleNamespace(path="/"),
        headers=headers or {},
        body=body,
        client=SimpleNamespace(host="127.0.0.1"),
        state=SimpleNamespace(),
    )
    # starlette may look at request._headers; mimic minimally
    hdrs = []
    for k, v in (headers or {}).items():
        hdrs.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    request._headers = hdrs  # type: ignore
    return request


class DummyTaskManager:
    async def send_message(self, a2a_request):
        # return a simple valid JSON-RPC response
        return {"jsonrpc": "2.0", "id": a2a_request.get("id"), "result": "ok"}


@pytest.fixture(autouse=True)
def reset_auth():
    """Reset auth settings before and after each test."""
    orig_enabled = app_settings.auth.enabled
    orig_require = app_settings.auth.require_permissions
    orig_perms = dict(app_settings.auth.permissions)
    app_settings.auth.enabled = False
    app_settings.auth.require_permissions = False
    yield
    app_settings.auth.enabled = orig_enabled
    app_settings.auth.require_permissions = orig_require
    app_settings.auth.permissions = orig_perms


@pytest.mark.asyncio
async def test_agent_run_requires_authentication():
    """Requests to the A2A endpoint should be rejected when auth is enabled."""
    app_settings.auth.enabled = True
    # prepare dummy app with minimal task manager and handler mapping
    app = SimpleNamespace(task_manager=DummyTaskManager())
    # ensure method handler exists
    app_settings.agent.method_handlers["message/send"] = "send_message"

    req = _make_a2a_request("message/send", {"message": {}})
    resp = await agent_run_endpoint(cast(BinduApplication, app), req)
    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert "Authentication" in body.get("error", "")


@pytest.mark.asyncio
async def test_agent_run_permission_enforced():
    """If permission checking is enabled, unauthorized scopes should be blocked."""
    app_settings.auth.enabled = True
    app_settings.auth.require_permissions = True
    # require a custom permission for message/send
    app_settings.auth.permissions["message/send"] = ["agent:write"]

    app = SimpleNamespace(task_manager=DummyTaskManager())
    app_settings.agent.method_handlers["message/send"] = "send_message"

    req = _make_a2a_request("message/send", {"message": {}})
    # simulate authenticated user with no scopes
    req.state.user_info = {"scope": []}

    resp = await agent_run_endpoint(cast(BinduApplication, app), req)
    assert resp.status_code == 403
    body = json.loads(resp.body)
    assert "permissions" in body.get("error", "").lower()

    # now give the proper scope and ensure it passes through
    req2 = _make_a2a_request("message/send", {"message": {}})
    req2.state.user_info = {"scope": ["agent:write"]}
    resp2 = await agent_run_endpoint(cast(BinduApplication, app), req2)
    assert resp2.status_code == 200
    body2 = json.loads(resp2.body)
    assert body2.get("result") == "ok"
