import json
import logging
from types import SimpleNamespace
from uuid import UUID, uuid4

from starlette.testclient import TestClient

from bindu.server.applications import BinduApplication
import bindu.server.endpoints.a2a_protocol as a2a_protocol
from bindu.server.middleware import a2a as a2a_middleware


def _make_minimal_manifest():
    return SimpleNamespace(
        capabilities={"extensions": []},
        url="http://localhost:3773",
        name="test_agent",
    )


class _DummyTaskManager:
    is_running = True

    async def send_message(self, request):
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": request["params"]["message"],
        }


def _make_client():
    app = BinduApplication(manifest=_make_minimal_manifest(), debug=True)
    app.task_manager = _DummyTaskManager()
    return TestClient(app)


def _valid_message_send_payload():
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


def test_request_id_auto_generation():
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    client = _make_client()

    resp = client.post("/", json=_valid_message_send_payload())

    assert resp.status_code == 200
    header_value = resp.headers.get("X-Request-ID")
    assert header_value is not None
    UUID(header_value)


def test_request_id_passthrough_from_header():
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    client = _make_client()

    resp = client.post(
        "/",
        json=_valid_message_send_payload(),
        headers={"X-Request-ID": "test-request"},
    )

    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == "test-request"


def test_trace_id_auto_generation():
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    client = _make_client()

    resp = client.post("/", json=_valid_message_send_payload())

    assert resp.status_code == 200
    header_value = resp.headers.get("X-Trace-Id")
    assert header_value is not None
    UUID(header_value)


def test_trace_id_passthrough_from_header():
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    client = _make_client()

    resp = client.post(
        "/",
        json=_valid_message_send_payload(),
        headers={"X-Trace-Id": "trace-test"},
    )

    assert resp.status_code == 200
    assert resp.headers.get("X-Trace-Id") == "trace-test"


def test_structured_logging_invocation(caplog):
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    client = _make_client()

    caplog.set_level(
        logging.INFO, logger="bindu.server.endpoints.a2a_protocol")
    resp = client.post("/", json=_valid_message_send_payload())

    assert resp.status_code == 200
    assert any(
        isinstance(record.msg, dict) and record.msg.get(
            "event") == "a2a_request"
        for record in caplog.records
    )


def test_structured_logging_latency_measurement(monkeypatch, caplog):
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    client = _make_client()

    perf_counter_value = 1.0

    def fake_perf_counter():
        nonlocal perf_counter_value
        value = perf_counter_value
        perf_counter_value += 0.123
        return value

    monkeypatch.setattr(a2a_middleware.time, "perf_counter", fake_perf_counter)
    caplog.set_level(
        logging.INFO, logger="bindu.server.endpoints.a2a_protocol")

    resp = client.post(
        "/",
        json=_valid_message_send_payload(),
        headers={"X-Trace-Id": "trace-latency"},
    )

    assert resp.status_code == 200
    record = next(
        record.msg
        for record in caplog.records
        if isinstance(record.msg, dict)
        and record.msg.get("event") == "a2a_request"
    )
    assert record["trace_id"] == "trace-latency"
    assert record["method"] == "message/send"
    assert record["status_code"] == 200
    assert record["client_ip"] is not None
    assert record["latency_ms"] >= 123.0


def test_rate_limit_exceeded(monkeypatch):
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    monkeypatch.setattr(a2a_middleware, "RATE_LIMIT_MAX_REQUESTS", 2)
    client = _make_client()

    payload = _valid_message_send_payload()
    assert client.post("/", json=payload).status_code == 200
    assert client.post("/", json=payload).status_code == 200

    resp = client.post("/", json=payload)
    assert resp.status_code == 429
    body = json.loads(resp.text)
    assert body["error"]["code"] == -32000


def test_rate_limit_resets_after_window(monkeypatch):
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    monkeypatch.setattr(a2a_middleware, "RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(a2a_middleware, "RATE_LIMIT_WINDOW_SECONDS", 60)

    now = 1_000.0

    def fake_time():
        return now

    monkeypatch.setattr(a2a_middleware.time, "time", fake_time)
    client = _make_client()

    payload = _valid_message_send_payload()
    assert client.post("/", json=payload).status_code == 200
    assert client.post("/", json=payload).status_code == 429

    now = 1_000.0 + 61
    assert client.post("/", json=payload).status_code == 200


def test_valid_message_send_still_passes():
    a2a_middleware.RATE_LIMIT_BUCKETS.clear()
    client = _make_client()

    resp = client.post("/", json=_valid_message_send_payload())
    assert resp.status_code == 200
