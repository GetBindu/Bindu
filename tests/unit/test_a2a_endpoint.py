"""Unit tests for A2A protocol endpoint focusing on authentication/authorization."""

import json
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from starlette.requests import Request

from bindu.server.endpoints.a2a_protocol import agent_run_endpoint
from bindu.server.applications import BinduApplication
from bindu.settings import app_settings
from tests.utils import create_test_message


def _to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _convert_keys_to_camel(obj):
    """Recursively convert dict keys from snake_case to camelCase."""
    if isinstance(obj, dict):
        return {_to_camel_case(k): _convert_keys_to_camel(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_keys_to_camel(item) for item in obj]
    else:
        return obj


def _make_a2a_request(
    method: str, params: dict | None = None, headers: dict | None = None
) -> Request:
    """Create a minimal request object that mimics Starlette Request for A2A."""
    data = {"jsonrpc": "2.0", "id": str(uuid4()), "method": method}
    if params is not None:
        # Convert snake_case keys to camelCase for JSON-RPC validation
        data["params"] = _convert_keys_to_camel(params)
    raw = json.dumps(data, default=str).encode()

    # Initialize sent flag before async function
    sent_flag = {"value": False}

    async def receive():
        if sent_flag["value"]:
            return {"type": "http.disconnect"}
        sent_flag["value"] = True
        return {"type": "http.request", "body": raw, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in (headers or {}).items()
        ],
        "client": ("127.0.0.1", 1234),
    }
    request = Request(scope, receive)
    request.state.user_info = None  # type: ignore
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

    message = create_test_message(text="test")
    config = {"acceptedOutputModes": ["text/plain"]}
    req = _make_a2a_request(
        "message/send", {"message": message, "configuration": config}
    )
    resp = await agent_run_endpoint(cast(BinduApplication, app), req)  # type: ignore
    assert resp.status_code == 401
    body = json.loads(resp.body)
    assert "error" in body
    assert "Authentication" in body["error"]["message"]


@pytest.mark.asyncio
async def test_agent_run_permission_enforced():
    """If permission checking is enabled, unauthorized scopes should be blocked."""
    app_settings.auth.enabled = True
    app_settings.auth.require_permissions = True
    # require a custom permission for message/send
    app_settings.auth.permissions["message/send"] = ["agent:write"]

    app = SimpleNamespace(task_manager=DummyTaskManager())
    app_settings.agent.method_handlers["message/send"] = "send_message"

    message = create_test_message(text="test")
    config = {"acceptedOutputModes": ["text/plain"]}
    req = _make_a2a_request(
        "message/send", {"message": message, "configuration": config}
    )
    # simulate authenticated user with no scopes
    req.state.user_info = {"scope": []}  # type: ignore

    resp = await agent_run_endpoint(cast(BinduApplication, app), req)  # type: ignore
    assert resp.status_code == 403
    body = json.loads(resp.body)
    assert "error" in body
    assert "permissions" in body["error"]["message"].lower()

    # now give the proper scope and ensure it passes through
    message2 = create_test_message(text="test")
    config2 = {"acceptedOutputModes": ["text/plain"]}
    req2 = _make_a2a_request(
        "message/send", {"message": message2, "configuration": config2}
    )
    req2.state.user_info = {"scope": ["agent:write"]}  # type: ignore
    resp2 = await agent_run_endpoint(cast(BinduApplication, app), req2)  # type: ignore
    assert resp2.status_code == 200
    body2 = json.loads(resp2.body)
    assert body2.get("result") == "ok"
