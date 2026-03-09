# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Unit tests for negotiation endpoint."""

import json
from types import SimpleNamespace
from typing import cast

import pytest
from starlette.requests import Request

from bindu.server.applications import BinduApplication
from bindu.server.endpoints.negotiation import negotiation_endpoint


def _make_request(body: dict, headers: dict | None = None) -> Request:
    """Create a minimal mock request object with JSON body.

    The returned object includes a `state` attribute so tests can inject
    authentication info if needed.
    """
    body_bytes = json.dumps(body).encode("utf-8")

    # Initialize sent flag before async function
    sent_flag = {"value": False}

    async def receive():
        if sent_flag["value"]:
            return {"type": "http.disconnect"}
        sent_flag["value"] = True
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/agent/negotiation",
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


def _make_app_with_manifest(skills: list, x402: dict | None = None) -> object:
    """Create a minimal mock app with skills and optional x402."""
    capabilities = {"extensions": [x402] if x402 else []}
    manifest = SimpleNamespace(skills=skills, x402=x402, capabilities=capabilities)
    return SimpleNamespace(manifest=manifest, scheduler=None, task_manager=None)


@pytest.fixture(autouse=True)
def _disable_auth_settings():
    """Ensure authentication is disabled by default for most tests."""
    from bindu.settings import app_settings

    orig_enabled = app_settings.auth.enabled
    orig_require = app_settings.auth.require_permissions
    app_settings.auth.enabled = False
    app_settings.auth.require_permissions = False
    yield
    app_settings.auth.enabled = orig_enabled
    app_settings.auth.require_permissions = orig_require


@pytest.mark.asyncio
async def test_negotiation_endpoint_missing_task_summary():
    """Test negotiation endpoint rejects requests without task_summary."""
    app = _make_app_with_manifest([])
    request = _make_request({})

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 400
    data = json.loads(response.body)
    assert "task_summary" in data["error"]


@pytest.mark.asyncio
async def test_negotiation_endpoint_basic_acceptance():
    """Test negotiation endpoint accepts well-matched task."""
    skills = [
        {
            "id": "summarizer",
            "name": "Document Summarizer",
            "tags": ["summarization", "document", "text"],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
        }
    ]
    app = _make_app_with_manifest(skills)
    request = _make_request({"task_summary": "summarize this document"})

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["accepted"] is True
    assert data["score"] > 0
    assert "confidence" in data
    assert "subscores" in data


@pytest.mark.asyncio
async def test_negotiation_endpoint_rejection():
    """Test negotiation endpoint rejects mismatched task."""
    skills = [
        {
            "id": "calculator",
            "name": "Math Calculator",
            "tags": ["math", "calculator"],
        }
    ]
    app = _make_app_with_manifest(skills)
    request = _make_request(
        {
            "task_summary": "translate this document",
            "input_mime_types": ["application/pdf"],  # Not supported
        }
    )

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["accepted"] is False
    assert "rejection_reason" in data


@pytest.mark.asyncio
async def test_negotiation_endpoint_with_constraints():
    """Test negotiation endpoint with various constraints."""
    skills = [
        {
            "id": "processor",
            "name": "Data Processor",
            "tags": ["processing", "data"],
            "input_modes": ["text/plain", "application/json"],
            "output_modes": ["application/json"],
            "performance": {"avg_processing_time_ms": 1000},
            "allowed_tools": ["web_browser", "file_system"],
        }
    ]
    app = _make_app_with_manifest(skills)
    request = _make_request(
        {
            "task_summary": "process data",
            "input_mime_types": ["application/json"],
            "output_mime_types": ["application/json"],
            "max_latency_ms": 5000,
            "required_tools": ["web_browser"],
        }
    )

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["accepted"] is True
    assert data["latency_estimate_ms"] == 1000


@pytest.mark.asyncio
async def test_negotiation_endpoint_custom_weights():
    """Test negotiation endpoint with custom scoring weights."""
    skills = [
        {
            "id": "processor",
            "name": "Processor",
            "tags": ["processing"],
        }
    ]
    app = _make_app_with_manifest(skills)
    request = _make_request(
        {
            "task_summary": "process something",
            "weights": {
                "skill_match": 0.9,
                "io_compatibility": 0.025,
                "performance": 0.025,
                "load": 0.025,
                "cost": 0.025,
            },
        }
    )

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    # With heavy skill_match weight, should accept if keywords match
    assert "accepted" in data
    assert "subscores" in data


@pytest.mark.asyncio
async def test_negotiation_endpoint_invalid_weights():
    """Test negotiation endpoint rejects invalid weights."""
    skills = [{"id": "test", "name": "Test"}]
    app = _make_app_with_manifest(skills)
    request = _make_request(
        {
            "task_summary": "test",
            "weights": {
                "skill_match": -0.5,  # Negative weight is invalid
            },
        }
    )

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 400
    data = json.loads(response.body)
    assert "Invalid weights" in data["error"]


@pytest.mark.asyncio
async def test_negotiation_endpoint_with_x402():
    """Test negotiation endpoint with x402 pricing extension."""
    skills = [
        {
            "id": "premium-service",
            "name": "Premium Service",
            "tags": ["premium", "service"],
        }
    ]
    x402 = {"amount": "10.00", "currency": "USD"}
    app = _make_app_with_manifest(skills, x402=x402)
    request = _make_request(
        {"task_summary": "premium service task", "max_cost_amount": "50.00"}
    )

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    # Should not reject due to cost (10 < 50)
    assert "subscores" in data
    assert "cost" in data["subscores"]


@pytest.mark.asyncio
async def test_negotiation_endpoint_skill_matches():
    """Test that skill matches are included in response."""
    skills = [
        {
            "id": "analyzer",
            "name": "Text Analyzer",
            "tags": ["analysis", "text", "nlp"],
        },
        {
            "id": "processor",
            "name": "Text Processor",
            "tags": ["processing", "text"],
        },
    ]
    app = _make_app_with_manifest(skills)
    request = _make_request({"task_summary": "analyze and process text"})

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert "skill_matches" in data
    assert len(data["skill_matches"]) > 0
    # Each match should have expected fields
    for match in data["skill_matches"]:
        assert "skill_id" in match
        assert "skill_name" in match
        assert "score" in match


# -----------------------------------------------------------------------------
# Authentication tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_negotiation_requires_auth():
    """Verify endpoint rejects requests when authentication is enabled."""
    from bindu.settings import app_settings

    # enable auth globally
    app_settings.auth.enabled = True
    app_settings.auth.require_permissions = False

    app = _make_app_with_manifest([])
    request = _make_request({"task_summary": "foo"})
    # leave request.state empty so middleware did not run

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore
    assert response.status_code == 401
    data = json.loads(response.body)
    assert "error" in data
    assert "Authentication" in data["error"]["message"]

    # restore auth state (fixture will do this on teardown)


@pytest.mark.asyncio
async def test_negotiation_allows_when_authenticated():
    """Endpoint should allow requests if user_info is present."""
    from bindu.settings import app_settings

    app_settings.auth.enabled = True
    app_settings.auth.require_permissions = False

    app = _make_app_with_manifest([])
    request = _make_request({"task_summary": "foo"})
    request.state.user_info = {"scope": ["irrelevant"]}  # type: ignore

    response = await negotiation_endpoint(cast(BinduApplication, app), request)  # type: ignore
    # since manifest is missing, we expect 500, but not an auth error
    assert response.status_code != 401

    # auth state will be reset by fixture
