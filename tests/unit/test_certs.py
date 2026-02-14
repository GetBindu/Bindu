import shutil
import tempfile
from pathlib import Path

import pytest
from cryptography import x509

from bindu.auth.certs import CertificateManager, CertificateAuthority


@pytest.fixture
def cert_dir():
    """Create a temporary directory for certificates."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


def test_certificate_authority_creation(cert_dir):
    """Test that a CA can be created and files are generated."""
    ca = CertificateAuthority(cert_dir / "ca")

    assert (cert_dir / "ca" / "root_ca.key").exists()
    assert (cert_dir / "ca" / "root_ca.crt").exists()
    assert ca.ca_key is not None
    assert ca.ca_cert is not None


def test_agent_certificate_issuance(cert_dir):
    """Test that an agent certificate can be issued by the CA."""
    # 1. Setup CA
    ca = CertificateAuthority(cert_dir / "ca")

    # 2. Setup Manager with CA
    manager = CertificateManager(cert_dir / "agent", ca_manager=ca)

    # 3. Issue Certificate
    did = "did:bindu:agent:test-123"
    dns_names = ["test-agent.local"]
    ip_addresses = ["127.0.0.1"]

    success = manager.ensure_certificate(did, dns_names, ip_addresses)

    assert success is True
    assert (cert_dir / "agent" / "agent.key").exists()
    assert (cert_dir / "agent" / "agent.crt").exists()
    assert (cert_dir / "agent" / "ca.crt").exists()

    # 4. Verify Certificate Content
    with open(cert_dir / "agent" / "agent.crt", "rb") as f:
        cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)

    # Check Subject
    assert cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value == did

    # Check Issuer (should be CA)
    assert cert.issuer == ca.ca_cert.subject

    # Check SANs
    san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    san_names = san_ext.value.get_values_for_type(x509.DNSName)
    assert "test-agent.local" in san_names
    assert "localhost" in san_names  # Added by default


def test_certificate_renewal_needed(cert_dir):
    """Test that validity check detects missing certs."""
    manager = CertificateManager(cert_dir / "agent")
    assert manager._check_certificate_validity() is False


def test_ssl_context_creation(cert_dir):
    """Test SSL context creation from generated certs."""
    ca = CertificateAuthority(cert_dir / "ca")
    manager = CertificateManager(cert_dir / "agent", ca_manager=ca)
    manager.ensure_certificate("did:bindu:test")

    ssl_context = manager.get_ssl_context()
    assert ssl_context is not None
    import ssl

    assert ssl_context.verify_mode == ssl.CERT_REQUIRED
