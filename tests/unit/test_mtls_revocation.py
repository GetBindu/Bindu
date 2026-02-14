from unittest.mock import MagicMock, patch
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.applications import Starlette

from bindu.server.middleware.mtls import MTLSMiddleware
from bindu.settings import app_settings


# Mock classes
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
@patch("bindu.server.middleware.mtls.x509.load_pem_x509_crl")
@patch("bindu.server.middleware.mtls.Path.exists")
@patch("builtins.open")
def test_mtls_revoked_cert(
    mock_open, mock_path_exists, mock_load_crl, mock_load_cert, mtls_app
):
    """Test that revoked certificates are rejected."""
    app_settings.security.mtls_enabled = True

    # Mock Certificate
    mock_cert = MagicMock()
    mock_name_attr = MagicMock()
    mock_name_attr.value = "did:bindu:revoked"
    mock_cert.subject.get_attributes_for_oid.return_value = [mock_name_attr]
    mock_cert.serial_number = 12345

    # Valid dates
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    mock_cert.not_valid_before_utc = now - timedelta(days=1)
    mock_cert.not_valid_after_utc = now + timedelta(days=365)

    mock_load_cert.return_value = mock_cert

    # Mock CRL
    mock_path_exists.return_value = True
    mock_crl = MagicMock()
    mock_revoked_entry = MagicMock()
    # Return a mocked revoked entry for serial 12345
    mock_crl.get_revoked_certificate_by_serial_number.return_value = mock_revoked_entry
    mock_load_crl.return_value = mock_crl

    ssl_obj = MockSSLObject(cert_data=b"fake-cert")
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
    assert "revoked" in response.body.decode()
