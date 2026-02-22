from types import SimpleNamespace
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from bindu.server.applications import BinduApplication
from bindu.server.middleware.a2a import A2AMiddleware
from bindu.settings import app_settings
import bindu.server.endpoints.a2a_protocol as a2a_protocol


EVENTS: list[str] = []


class FirstMiddleware(A2AMiddleware):
    async def before_request(self, request, payload):
        EVENTS.append("first_before")

    async def after_response(self, request, response):
        EVENTS.append("first_after")
        return response

    async def on_error(self, request, error):
        EVENTS.append("first_error")
        if isinstance(error, JSONResponse):
            return error
        return None


class SecondMiddleware(A2AMiddleware):
    async def before_request(self, request, payload):
        EVENTS.append("second_before")

    async def after_response(self, request, response):
        EVENTS.append("second_after")
        return response

    async def on_error(self, request, error):
        EVENTS.append("second_error")
        if isinstance(error, JSONResponse):
            return error
        return None


class ShortCircuitMiddleware(A2AMiddleware):
    async def before_request(self, request, payload):
        EVENTS.append("short_circuit_before")
        return JSONResponse({"jsonrpc": "2.0", "id": "1", "result": {"ok": True}})


class ErrorMiddleware(A2AMiddleware):
    async def before_request(self, request, payload):
        EVENTS.append("error_before")
        raise RuntimeError("boom")

    async def on_error(self, request, error):
        EVENTS.append("error_on_error")


class ResponseModifierMiddleware(A2AMiddleware):
    async def after_response(self, request, response):
        EVENTS.append("modify_after")
        response.headers["X-Modified"] = "1"
        return response


class _DummyTaskManager:
    is_running = True

    def __init__(self):
        self.called = False

    async def send_message(self, request):
        self.called = True
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": request["params"]["message"],
        }


def _make_client(task_manager):
    manifest = SimpleNamespace(
        capabilities={"extensions": []},
        url="http://localhost:3773",
        name="test_agent",
    )
    app = BinduApplication(manifest=manifest, debug=True)
    app.task_manager = task_manager
    return TestClient(app)


def _payload():
    return {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/send",
        "params": {
            "configuration": {"acceptedOutputModes": ["text/plain"]},
            "message": {
                "messageId": str(uuid4()),
                "contextId": str(uuid4()),
                "taskId": str(uuid4()),
                "kind": "message",
                "role": "user",
                "parts": [{"kind": "text", "text": "hello"}],
            },
        },
    }


def _set_middlewares(monkeypatch, middleware_paths):
    monkeypatch.setattr(app_settings.agent,
                        "a2a_middlewares", middleware_paths)
    a2a_protocol._A2A_MIDDLEWARE_CACHE.clear()


def test_middleware_execution_order(monkeypatch):
    EVENTS.clear()
    _set_middlewares(
        monkeypatch,
        [
            "tests.unit.test_a2a_middleware_pipeline.FirstMiddleware",
            "tests.unit.test_a2a_middleware_pipeline.SecondMiddleware",
        ],
    )

    client = _make_client(_DummyTaskManager())
    resp = client.post("/", json=_payload())

    assert resp.status_code == 200
    assert EVENTS == [
        "first_before",
        "second_before",
        "first_after",
        "second_after",
    ]


def test_middleware_error_propagation(monkeypatch):
    EVENTS.clear()
    _set_middlewares(
        monkeypatch,
        [
            "tests.unit.test_a2a_middleware_pipeline.FirstMiddleware",
            "tests.unit.test_a2a_middleware_pipeline.ErrorMiddleware",
        ],
    )

    client = _make_client(_DummyTaskManager())
    resp = client.post("/", json=_payload())

    assert resp.status_code == 500
    assert EVENTS == ["first_before", "error_before",
                      "error_on_error", "first_error"]


def test_middleware_short_circuit(monkeypatch):
    EVENTS.clear()
    task_manager = _DummyTaskManager()
    _set_middlewares(
        monkeypatch,
        ["tests.unit.test_a2a_middleware_pipeline.ShortCircuitMiddleware"],
    )

    client = _make_client(task_manager)
    resp = client.post("/", json=_payload())

    assert resp.status_code == 200
    assert task_manager.called is False
    assert EVENTS == ["short_circuit_before"]


def test_middleware_can_modify_response(monkeypatch):
    EVENTS.clear()
    _set_middlewares(
        monkeypatch,
        ["tests.unit.test_a2a_middleware_pipeline.ResponseModifierMiddleware"],
    )

    client = _make_client(_DummyTaskManager())
    resp = client.post("/", json=_payload())

    assert resp.status_code == 200
    assert resp.headers.get("X-Modified") == "1"
    assert EVENTS == ["modify_after"]
