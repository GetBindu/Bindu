from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.applications import Starlette

from bindu.server.middleware.mtls import MTLSMiddleware
from bindu.settings import app_settings


# Mock classes tailored for this test
class MockSSLObject:
    def __init__(self, cert_data=None):
        self.cert_data = cert_data

    def getpeercert(self, binary_form=False):
        return self.cert_data


class MockTransport:
    def __init__(self, ssl_object):
        self.ssl_object = ssl_object

    def get_extra_info(self, name):
        if name == "ssl_object":
            return self.ssl_object
        return None


@pytest.fixture
def mtls_app():
    app = Starlette()
    app.add_middleware(MTLSMiddleware)

    @app.route("/")
    async def homepage(request):
        return JSONResponse({"did": getattr(request.state, "client_did", "unknown")})

    return app


@patch("bindu.server.middleware.mtls.x509.load_der_x509_certificate")
def test_mtls_expired_cert(mock_load_cert, mtls_app):
    """Test that expired certificates are rejected."""
    app_settings.security.mtls_enabled = True

    # Mock Certificate that is expired
    mock_cert = MagicMock()
    mock_name_attr = MagicMock()
    mock_name_attr.value = "did:bindu:expired"
    mock_cert.subject.get_attributes_for_oid.return_value = [mock_name_attr]

    # Set expired dates
    now = datetime.now(timezone.utc)
    mock_cert.not_valid_before_utc = now - timedelta(days=365)
    mock_cert.not_valid_after_utc = now - timedelta(days=1)  # Expired yesterday

    mock_load_cert.return_value = mock_cert

    ssl_obj = MockSSLObject(cert_data=b"fake-expired-cert")
    transport = MockTransport(ssl_obj)

    middleware = MTLSMiddleware(mtls_app)

    async def mock_call_next(request):
        return JSONResponse({"ok": True})

    scope = {"type": "http", "transport": transport}
    request = Request(scope)

    import asyncio

    # We expect a 401 response
    response = asyncio.run(middleware.dispatch(request, mock_call_next))

    assert response.status_code == 401
    assert "expired" in response.body.decode()
