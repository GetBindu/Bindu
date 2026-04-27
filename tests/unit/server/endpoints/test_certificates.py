"""Unit tests for mTLS certificate lifecycle endpoints."""
import pytest
from bindu.server.endpoints.certificates import (
    compute_sha256_fingerprint,
    CertificateNotFoundError,
    CertificateBindingError,
    _get_caller_did,
    _authorize_agent_did,
)
from unittest.mock import MagicMock


def test_compute_sha256_fingerprint_returns_string():
    """compute_sha256_fingerprint returns a non-empty hex string."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from datetime import datetime, timezone, timedelta

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Test"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    fingerprint = compute_sha256_fingerprint(pem)
    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 64  # SHA-256 hex = 64 chars


def test_authorize_agent_did_returns_none_when_authorized():
    """Returns None when caller_did matches requested_did."""
    result = _authorize_agent_did(
        "did:bindu:test:agent:123",
        "did:bindu:test:agent:123",
    )
    assert result is None


def test_authorize_agent_did_returns_401_when_unauthenticated():
    """Returns 401 when caller_did is None."""
    from starlette.responses import JSONResponse
    result = _authorize_agent_did(None, "did:bindu:test:agent:123")
    assert isinstance(result, JSONResponse)
    assert result.status_code == 401


def test_authorize_agent_did_returns_403_when_forbidden():
    """Returns 403 when caller_did does not match requested_did."""
    from starlette.responses import JSONResponse
    result = _authorize_agent_did(
        "did:bindu:test:agent:attacker",
        "did:bindu:test:agent:victim",
    )
    assert isinstance(result, JSONResponse)
    assert result.status_code == 403


def test_get_caller_did_returns_none_when_not_set():
    """Returns None when request.state has no agent_did."""
    request = MagicMock()
    del request.state.agent_did
    type(request.state).agent_did = property(
        lambda self: (_ for _ in ()).throw(AttributeError())
    )
    result = _get_caller_did(request)
    assert result is None


def test_certificate_not_found_error_is_value_error():
    """CertificateNotFoundError inherits from ValueError."""
    assert issubclass(CertificateNotFoundError, ValueError)


def test_certificate_binding_error_is_runtime_error():
    """CertificateBindingError inherits from RuntimeError."""
    assert issubclass(CertificateBindingError, RuntimeError)