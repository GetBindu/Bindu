"""Integration tests for x402 payment flow end-to-end behavior.

Covers:
- successful paid task request and settlement
- insufficient balance (verification failure)
- payment session timeout
- settlement failure after successful task execution
"""

from __future__ import annotations

import json
import time
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.responses import JSONResponse

from bindu.extensions.x402 import X402AgentExtension
from bindu.server.applications import BinduApplication
from bindu.settings import app_settings
from tests.mocks import MockAgent, MockManifest

pytestmark = pytest.mark.x402


class _NoopSpanContext:
    """Minimal context manager used to patch tracing spans in tests."""

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


def _build_paid_app() -> BinduApplication:
    """Create a Bindu app with x402 payment enabled."""
    manifest = MockManifest(agent_fn=MockAgent(response="Paid task completed"))
    manifest.url = "http://localhost:3773"
    manifest.capabilities.setdefault("extensions", []).append(
        X402AgentExtension(
            amount="10000",
            token="USDC",
            network="base-sepolia",
            pay_to_address="0x1234567890123456789012345678901234567890",
            required=True,
        )
    )

    return BinduApplication(manifest=manifest, url=manifest.url)


def _message_send_payload() -> dict:
    """Create a minimal valid JSON-RPC message/send payload."""
    context_id = str(uuid4())
    task_id = str(uuid4())

    return {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "configuration": {
                "acceptedOutputModes": ["application/json"],
            },
            "message": {
                "messageId": str(uuid4()),
                "contextId": context_id,
                "taskId": task_id,
                "kind": "message",
                "role": "user",
                "parts": [{"kind": "text", "text": "Run a paid task"}],
            }
        },
    }


def _task_get_payload(task_id: str) -> dict:
    """Create a JSON-RPC tasks/get payload."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "tasks/get",
        "params": {"taskId": task_id},
    }


def _payment_header_value() -> str:
    """Create a payment header value parsable by test stubs.

    tests/conftest.py stubs safe_base64_decode to return raw bytes,
    so we pass plain JSON text (instead of base64) for test integration.
    """
    payment_payload = {
        "x402Version": 1,
        "scheme": "exact",
        "network": "base-sepolia",
        "payload": {
            "authorization": {
                "from": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
                "to": "0x1234567890123456789012345678901234567890",
                "value": "10000",
            }
        },
    }
    return json.dumps(payment_payload)


def _wait_for_task_terminal_state(
    client: TestClient, task_id: str, timeout_seconds: float = 5.0
) -> dict:
    """Poll task status until it reaches a terminal state."""
    deadline = time.time() + timeout_seconds
    last_task = None

    while time.time() < deadline:
        resp = client.post("/", json=_task_get_payload(task_id))
        assert resp.status_code == 200
        body = resp.json()
        assert "result" in body

        last_task = body["result"]
        state = last_task.get("status", {}).get("state")
        if state in app_settings.agent.terminal_states:
            return last_task

        time.sleep(0.05)

    pytest.fail(f"Task {task_id} did not reach terminal state; last={last_task}")


def test_paid_task_request_successful_payment_and_settlement():
    """End-to-end paid task request completes and attaches settlement receipt."""
    app = _build_paid_app()

    with patch(
        "bindu.server.middleware.x402.x402_middleware.find_matching_payment_requirements"
    ) as mock_find_requirements, patch(
        "bindu.server.middleware.x402.x402_middleware.X402Middleware._validate_payment_manually",
        new=AsyncMock(return_value=(True, None)),
    ), patch(
        "bindu.server.workers.base.tracer.start_as_current_span",
        side_effect=lambda *args, **kwargs: _NoopSpanContext(),
    ), patch("x402.facilitator.FacilitatorClient") as mock_facilitator_cls:
        mock_find_requirements.side_effect = lambda reqs, _payload: reqs[0] if reqs else None

        settle_response = MagicMock()
        settle_response.success = True
        settle_response.model_dump.return_value = {"receipt": "receipt-ok"}

        facilitator_instance = MagicMock()
        facilitator_instance.settle = AsyncMock(return_value=settle_response)
        mock_facilitator_cls.return_value = facilitator_instance

        with TestClient(app) as client:
            send_resp = client.post(
                "/",
                json=_message_send_payload(),
                headers={"X-PAYMENT": _payment_header_value()},
            )

            assert send_resp.status_code == 200
            send_body = send_resp.json()
            task_id = send_body["result"]["id"]

            task = _wait_for_task_terminal_state(client, task_id)
            assert task["status"]["state"] == "completed"

            metadata = task.get("metadata", {})
            assert (
                metadata.get(app_settings.x402.meta_status_key)
                == app_settings.x402.status_completed
            )
            assert app_settings.x402.meta_receipts_key in metadata
            assert metadata[app_settings.x402.meta_receipts_key][0]["receipt"] == "receipt-ok"


def test_paid_task_request_insufficient_balance_returns_402():
    """When payment validation fails (insufficient balance), request is rejected."""
    app = _build_paid_app()

    with patch(
        "bindu.server.middleware.x402.x402_middleware.find_matching_payment_requirements"
    ) as mock_find_requirements, patch(
        "bindu.server.middleware.x402.x402_middleware.X402Middleware._validate_payment_manually",
        new=AsyncMock(return_value=(False, "Insufficient balance")),
    ), patch(
        "bindu.server.middleware.x402.x402_middleware.X402Middleware._create_402_response",
        return_value=JSONResponse(
            content={"error": "Invalid payment: Insufficient balance"},
            status_code=402,
        ),
    ):
        mock_find_requirements.side_effect = lambda reqs, _payload: reqs[0] if reqs else None

        with TestClient(app) as client:
            send_resp = client.post(
                "/",
                json=_message_send_payload(),
                headers={"X-PAYMENT": _payment_header_value()},
            )

            assert send_resp.status_code == 402
            body = send_resp.json()
            assert "error" in body
            assert "Insufficient balance" in body["error"]


def test_payment_session_wait_timeout_returns_not_found():
    """Payment status wait mode returns not-found when wait times out."""
    app = _build_paid_app()

    with TestClient(app) as client:
        start_resp = client.post("/api/start-payment-session")
        assert start_resp.status_code == 200

        session_id = start_resp.json()["session_id"]

        # Simulate timeout behavior from wait_for_completion (returns None)
        app._payment_session_manager.wait_for_completion = AsyncMock(return_value=None)  # type: ignore[method-assign]

        status_resp = client.get(f"/api/payment-status/{session_id}?wait=true")
        assert status_resp.status_code == 404
        body = status_resp.json()
        assert "error" in body
        assert "not found" in body["error"].lower()


def test_paid_task_request_settlement_failure_marks_payment_failed():
    """Task completes but settlement failure metadata is recorded."""
    app = _build_paid_app()

    with patch(
        "bindu.server.middleware.x402.x402_middleware.find_matching_payment_requirements"
    ) as mock_find_requirements, patch(
        "bindu.server.middleware.x402.x402_middleware.X402Middleware._validate_payment_manually",
        new=AsyncMock(return_value=(True, None)),
    ), patch(
        "bindu.server.workers.base.tracer.start_as_current_span",
        side_effect=lambda *args, **kwargs: _NoopSpanContext(),
    ), patch("x402.facilitator.FacilitatorClient") as mock_facilitator_cls:
        mock_find_requirements.side_effect = lambda reqs, _payload: reqs[0] if reqs else None

        settle_response = MagicMock()
        settle_response.success = False
        settle_response.error_reason = "Settlement provider unavailable"

        facilitator_instance = MagicMock()
        facilitator_instance.settle = AsyncMock(return_value=settle_response)
        mock_facilitator_cls.return_value = facilitator_instance

        with TestClient(app) as client:
            send_resp = client.post(
                "/",
                json=_message_send_payload(),
                headers={"X-PAYMENT": _payment_header_value()},
            )

            assert send_resp.status_code == 200
            send_body = send_resp.json()
            task_id = send_body["result"]["id"]

            task = _wait_for_task_terminal_state(client, task_id)
            assert task["status"]["state"] == "completed"

            metadata = task.get("metadata", {})
            assert (
                metadata.get(app_settings.x402.meta_status_key)
                == app_settings.x402.status_failed
            )
            assert (
                metadata.get(app_settings.x402.meta_error_key)
                == "Settlement provider unavailable"
            )
