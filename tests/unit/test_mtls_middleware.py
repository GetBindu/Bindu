import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse

from bindu.server.middleware.mtls import MTLSMiddleware
from bindu.settings import app_settings


# Mock SSL Object
class MockSSLObject:
    def __init__(self, cert_data=None):
        self.cert_data = cert_data

    def getpeercert(self, binary_form=False):
        return self.cert_data


# Mock Transport
class MockTransport:
    def __init__(self, ssl_object):
        self.ssl_object = ssl_object

    def get_extra_info(self, name):
        if name == "ssl_object":
            return self.ssl_object
        return None


@pytest.fixture
def mock_cert_data():
    # minimalist DER cert mock (won't actually parse with x509 loader without real data)
    # So we'll need to mock the x509 loader too
    return b"fake-cert-data"


@pytest.fixture
def mtls_app():
    app = Starlette()
    app.add_middleware(MTLSMiddleware)

    @app.route("/")
    async def homepage(request):
        return JSONResponse({"did": getattr(request.state, "client_did", "unknown")})

    return app


def test_mtls_disabled_by_default(mtls_app):
    """Test that requests pass when mTLS is disabled."""
    app_settings.security.mtls_enabled = False
    with TestClient(mtls_app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"did": "unknown"}


def test_mtls_missing_cert(mtls_app):
    """Test that requests are rejected when mTLS enabled but no cert provided."""
    app_settings.security.mtls_enabled = True

    # Mock request without transport/ssl info
    with TestClient(mtls_app) as client:
        response = client.get("/")
        assert response.status_code == 401
        assert response.json()["detail"] == "Client certificate required"


@patch("bindu.server.middleware.mtls.x509.load_der_x509_certificate")
def test_mtls_valid_cert(mock_load_cert, mtls_app, mock_cert_data):
    """Test successful mTLS authentication."""
    app_settings.security.mtls_enabled = True

    # Mock Certificate Structure
    mock_cert = MagicMock()
    mock_name_attr = MagicMock()
    mock_name_attr.value = "did:bindu:test-agent"
    mock_cert.subject.get_attributes_for_oid.return_value = [mock_name_attr]

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    mock_cert.not_valid_before_utc = now - timedelta(days=1)
    mock_cert.not_valid_after_utc = now + timedelta(days=365)

    mock_load_cert.return_value = mock_cert

    # Setup mock transport with SSL object
    ssl_obj = MockSSLObject(cert_data=mock_cert_data)
    transport = MockTransport(ssl_obj)

    # We need to inject transport into the scope. TestClient doesn't easily support this.
    # So we verify the middleware logic directly or use a custom scope.

    # Alternative: Instantiate middleware directly and call it
    middleware = MTLSMiddleware(mtls_app)

    async def mock_call_next(request):
        return JSONResponse({"did": request.state.client_did})

    # Create a mock request with transport
    scope = {"type": "http", "transport": transport, "state": {}}
    from starlette.requests import Request

    request = Request(scope)

    # Run the dispatch method
    import asyncio

    response = asyncio.run(middleware.dispatch(request, mock_call_next))

    assert response.status_code == 200
    import json

    body = json.loads(response.body)
    assert body["did"] == "did:bindu:test-agent"


@patch("bindu.server.middleware.mtls.x509.load_der_x509_certificate")
def test_mtls_invalid_cert_structure(mock_load_cert, mtls_app, mock_cert_data):
    """Test mTLS with certificate missing Common Name."""
    app_settings.security.mtls_enabled = True

    # Mock Certificate with no Common Name
    mock_cert = MagicMock()
    mock_cert.subject.get_attributes_for_oid.return_value = []  # Content empty

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    mock_cert.not_valid_before_utc = now - timedelta(days=1)
    mock_cert.not_valid_after_utc = now + timedelta(days=365)

    mock_load_cert.return_value = mock_cert

    ssl_obj = MockSSLObject(cert_data=mock_cert_data)
    transport = MockTransport(ssl_obj)

    middleware = MTLSMiddleware(mtls_app)

    async def mock_call_next(request):
        return JSONResponse({"ok": True})

    scope = {"type": "http", "transport": transport}
    scope = {"type": "http", "transport": transport}
    from starlette.requests import Request

    request = Request(scope)

    import asyncio

    response = asyncio.run(middleware.dispatch(request, mock_call_next))

    assert response.status_code == 401
    assert "missing Common Name" in str(response.body)
