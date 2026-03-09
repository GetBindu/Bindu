"""Unit tests for A2A protocol endpoint focusing on authentication/authorization."""

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from starlette.requests import Request

from bindu.server.endpoints.a2a_protocol import _serialize_state_obj, agent_run_endpoint
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
async def test_agent_run_rejects_file_part_missing_text():
    """Validation should catch file parts that omit the required `text` field."""
    app = SimpleNamespace(task_manager=DummyTaskManager())
    app_settings.agent.method_handlers["message/send"] = "send_message"

    message = create_test_message(text="test")
    # attach an invalid file part without accompanying text
    message["parts"].append(
        {
            "kind": "file",
            "file": {"bytes": "dGVzdA==", "mimeType": "text/plain", "name": "test.txt"},
        }
    )
    config = {"acceptedOutputModes": ["text/plain"]}

    req = _make_a2a_request(
        "message/send", {"message": message, "configuration": config}
    )
    resp = await agent_run_endpoint(cast(BinduApplication, app), req)  # type: ignore
    assert resp.status_code == 400
    body = json.loads(resp.body)
    assert "error" in body
    # validation failure is treated as a JSON parse error (-32700) by
    # the endpoint wrapper, since the incoming payload couldn't be coerced to
    # the typed models.
    assert body["error"]["code"] == -32700


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


# ---------------------------------------------------------------------------
# Payment context attachment tests (guards the fix for the AttributeError bug)
# ---------------------------------------------------------------------------


class _PydanticLike:
    """Minimal stand-in for a Pydantic model (has model_dump)."""

    def __init__(self, data: dict):
        self._data = data

    def model_dump(self) -> dict:
        return dict(self._data)


@dataclass
class _DCLike:
    """Minimal dataclass to verify dataclasses.asdict() path."""

    value: str


def _make_message_send_request(extra_state: dict | None = None) -> Request:
    """Build a valid message/send A2A request with optional extra request.state attrs."""
    message = create_test_message(text="pay-test")
    data = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "message": {k: v for k, v in message.items()},
            "configuration": {"acceptedOutputModes": ["text/plain"]},
        },
    }
    raw = json.dumps(_convert_keys_to_camel(data), default=str).encode()
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
        "headers": [],
        "client": ("127.0.0.1", 9999),
    }
    req = Request(scope, receive)
    req.state.user_info = None  # type: ignore
    for attr, val in (extra_state or {}).items():
        setattr(req.state, attr, val)
    return req


@pytest.mark.asyncio
async def test_payment_context_attached_when_all_three_fields_present():
    """When all three payment state fields are set the context is forwarded."""
    captured: list[dict] = []

    class CapturingTaskManager:
        async def send_message(self, a2a_req):
            params = a2a_req.get("params", {})
            msg = params.get("message", {})
            captured.append(msg.get("metadata", {}))
            return {"jsonrpc": "2.0", "id": a2a_req.get("id"), "result": "ok"}

    app = SimpleNamespace(task_manager=CapturingTaskManager())
    app_settings.agent.method_handlers["message/send"] = "send_message"

    req = _make_message_send_request(
        {
            "payment_payload": _PydanticLike({"amount": 100}),
            "payment_requirements": _PydanticLike({"asset": "USDC"}),
            "verify_response": _PydanticLike({"is_valid": True}),
        }
    )

    resp = await agent_run_endpoint(cast(BinduApplication, app), req)  # type: ignore
    assert resp.status_code == 200
    assert len(captured) == 1
    ctx = captured[0].get("_payment_context")
    assert ctx is not None
    assert ctx["payment_payload"] == {"amount": 100}
    assert ctx["payment_requirements"] == {"asset": "USDC"}
    assert ctx["verify_response"] == {"is_valid": True}


@pytest.mark.asyncio
async def test_no_payment_context_when_only_partial_state_present():
    """If only some payment fields exist, no context is attached — no AttributeError."""
    captured: list[dict] = []

    class CapturingTaskManager:
        async def send_message(self, a2a_req):
            params = a2a_req.get("params", {})
            msg = params.get("message", {})
            captured.append(msg.get("metadata", {}))
            return {"jsonrpc": "2.0", "id": a2a_req.get("id"), "result": "ok"}

    app = SimpleNamespace(task_manager=CapturingTaskManager())
    app_settings.agent.method_handlers["message/send"] = "send_message"

    # Only payment_payload is present; the other two are missing entirely.
    req = _make_message_send_request({"payment_payload": _PydanticLike({"amount": 50})})

    resp = await agent_run_endpoint(cast(BinduApplication, app), req)  # type: ignore
    # Must not produce a 500 — the guard must handle the partial state gracefully.
    assert resp.status_code == 200
    assert len(captured) == 1
    # No _payment_context key should be present.
    assert "_payment_context" not in captured[0]


@pytest.mark.asyncio
async def test_no_payment_context_when_all_fields_absent():
    """If no payment fields are set at all, the request succeeds with no context."""
    captured: list[dict] = []

    class CapturingTaskManager:
        async def send_message(self, a2a_req):
            params = a2a_req.get("params", {})
            msg = params.get("message", {})
            captured.append(msg.get("metadata", {}))
            return {"jsonrpc": "2.0", "id": a2a_req.get("id"), "result": "ok"}

    app = SimpleNamespace(task_manager=CapturingTaskManager())
    app_settings.agent.method_handlers["message/send"] = "send_message"

    req = _make_message_send_request()  # no payment state at all

    resp = await agent_run_endpoint(cast(BinduApplication, app), req)  # type: ignore
    assert resp.status_code == 200
    assert "_payment_context" not in captured[0]


@pytest.mark.asyncio
async def test_serialization_error_is_non_fatal():
    """A payment object that cannot be serialized must not cause a 500."""

    class UnserializableObj:
        """Has no model_dump, is not a dataclass, and dict() on it raises."""

        def keys(self):
            raise RuntimeError("cannot serialize")

    captured: list[dict] = []

    class CapturingTaskManager:
        async def send_message(self, a2a_req):
            params = a2a_req.get("params", {})
            msg = params.get("message", {})
            captured.append(msg.get("metadata", {}))
            return {"jsonrpc": "2.0", "id": a2a_req.get("id"), "result": "ok"}

    app = SimpleNamespace(task_manager=CapturingTaskManager())
    app_settings.agent.method_handlers["message/send"] = "send_message"

    req = _make_message_send_request(
        {
            "payment_payload": UnserializableObj(),
            "payment_requirements": _PydanticLike({"asset": "USDC"}),
            "verify_response": _PydanticLike({"is_valid": True}),
        }
    )

    resp = await agent_run_endpoint(cast(BinduApplication, app), req)  # type: ignore
    # The serialization error is swallowed — no 500, no crash.
    assert resp.status_code == 200
    # _payment_context was intentionally omitted due to serialization failure.
    assert "_payment_context" not in captured[0]


# ---------------------------------------------------------------------------
# _serialize_state_obj unit tests
# ---------------------------------------------------------------------------


def test_serialize_pydantic_like():
    obj = _PydanticLike({"x": 1})
    assert _serialize_state_obj(obj) == {"x": 1}


def test_serialize_dataclass():
    obj = _DCLike(value="hello")
    assert _serialize_state_obj(obj) == {"value": "hello"}


def test_serialize_plain_dict_coercible():
    class DictLike:
        def keys(self):
            return ["a"]

        def __getitem__(self, key):
            return 99

    assert _serialize_state_obj(DictLike()) == {"a": 99}
