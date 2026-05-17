"""Tests for the CertStore leaf logic.

Covers the disk + crypto operations that ship in Phase 1. The step-ca client
and the orchestrator are stubs at this stage, so they have no tests yet.
"""

from __future__ import annotations

import platform
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from bindu.extensions.mtls import CertStore


@pytest.fixture
def store(tmp_path: Path) -> CertStore:
    """Bind a CertStore to a per-test tmp directory."""
    return CertStore(tmp_path)


class TestPathsAndExistence:
    def test_paths_live_under_pki_dir(self, tmp_path: Path, store: CertStore) -> None:
        assert store.cert_path.parent == tmp_path
        assert store.key_path.parent == tmp_path
        assert store.ca_bundle_path.parent == tmp_path
        assert store.csr_path.parent == tmp_path

    def test_has_cert_false_when_empty(self, store: CertStore) -> None:
        assert store.has_cert() is False
        assert store.has_ca_bundle() is False

    def test_has_cert_requires_both_files(self, store: CertStore) -> None:
        store.cert_path.write_bytes(b"cert")
        assert store.has_cert() is False  # key still missing
        store.key_path.write_bytes(b"key")
        assert store.has_cert() is True


class TestKeyGeneration:
    def test_generate_keypair_writes_pem(self, store: CertStore) -> None:
        private_key, key_pem = store.generate_keypair()
        assert isinstance(private_key, ec.EllipticCurvePrivateKey)
        assert b"BEGIN PRIVATE KEY" in key_pem  # pragma: allowlist secret
        assert store.key_path.is_file()

    def test_generate_keypair_uses_p256(self, store: CertStore) -> None:
        private_key, _ = store.generate_keypair()
        assert isinstance(private_key.curve, ec.SECP256R1)

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="POSIX permission bits are not enforced on Windows",
    )
    def test_private_key_written_with_owner_only_mode(self, store: CertStore) -> None:
        store.generate_keypair()
        mode = stat.S_IMODE(store.key_path.stat().st_mode)
        assert mode == 0o600

    def test_load_private_key_round_trips(self, store: CertStore) -> None:
        original, _ = store.generate_keypair()
        loaded = store.load_private_key()
        assert (
            loaded.private_numbers().private_value
            == original.private_numbers().private_value
        )

    def test_load_private_key_missing_raises(self, store: CertStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.load_private_key()


class TestCSRBuilding:
    DID = "did:bindu:raahul:test:abc123"

    def test_csr_contains_did_in_subject(self, store: CertStore) -> None:
        private_key, _ = store.generate_keypair()
        csr_pem = store.build_csr(private_key, self.DID)
        csr = x509.load_pem_x509_csr(csr_pem)
        cn_attr = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        assert cn_attr[0].value == self.DID

    def test_csr_includes_did_as_uri_san(self, store: CertStore) -> None:
        private_key, _ = store.generate_keypair()
        csr_pem = store.build_csr(private_key, self.DID)
        csr = x509.load_pem_x509_csr(csr_pem)
        san = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        uris = san.get_values_for_type(x509.UniformResourceIdentifier)
        assert self.DID in uris

    def test_csr_includes_dns_san_when_url_provided(self, store: CertStore) -> None:
        private_key, _ = store.generate_keypair()
        csr_pem = store.build_csr(
            private_key, self.DID, agent_url="https://agent.example.com/path"
        )
        csr = x509.load_pem_x509_csr(csr_pem)
        san = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        dns = san.get_values_for_type(x509.DNSName)
        assert "agent.example.com" in dns

    def test_csr_omits_dns_san_when_no_url(self, store: CertStore) -> None:
        private_key, _ = store.generate_keypair()
        csr_pem = store.build_csr(private_key, self.DID)
        csr = x509.load_pem_x509_csr(csr_pem)
        san = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        assert san.get_values_for_type(x509.DNSName) == []

    def test_csr_persisted_to_disk(self, store: CertStore) -> None:
        private_key, _ = store.generate_keypair()
        store.build_csr(private_key, self.DID)
        assert store.csr_path.is_file()
        assert b"BEGIN CERTIFICATE REQUEST" in store.csr_path.read_bytes()


class TestExpiryAndRenewal:
    def test_get_cert_expiry_none_when_missing(self, store: CertStore) -> None:
        assert store.get_cert_expiry() is None

    def test_is_renewal_due_true_when_missing(self, store: CertStore) -> None:
        assert store.is_renewal_due(renew_before_hours=8) is True

    def test_get_cert_fingerprint_none_when_missing(self, store: CertStore) -> None:
        assert store.get_cert_fingerprint() is None

    def test_get_cert_expiry_none_on_corrupt_file(self, store: CertStore) -> None:
        store.cert_path.write_bytes(b"not a real PEM")
        assert store.get_cert_expiry() is None
        assert store.is_renewal_due(8) is True

    def test_expiry_and_renewal_on_real_cert(self, store: CertStore) -> None:
        """End-to-end: write a self-signed cert and read back expiry + fingerprint."""
        private_key, _ = store.generate_keypair()
        not_before = datetime.now(timezone.utc) - timedelta(minutes=1)
        not_after = datetime.now(timezone.utc) + timedelta(hours=24)
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
            .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .sign(private_key, hashes.SHA256())
        )
        store.write_cert(cert.public_bytes(serialization.Encoding.PEM))

        expiry = store.get_cert_expiry()
        assert expiry is not None
        # Allow a 5s slop window for the date roundtrip through the X.509 encoder.
        assert abs((expiry - not_after).total_seconds()) < 5

        # 24h cert with an 8h renewal margin is still good.
        assert store.is_renewal_due(renew_before_hours=8) is False
        # But a 48h margin would force a renewal.
        assert store.is_renewal_due(renew_before_hours=48) is True

        fp = store.get_cert_fingerprint()
        assert fp is not None
        # Colon-separated hex bytes -> 32 octets, 95 chars.
        assert len(fp) == 95
        assert fp.count(":") == 31


class TestWritePermissions:
    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="POSIX permission bits are not enforced on Windows",
    )
    def test_cert_and_bundle_are_world_readable(self, store: CertStore) -> None:
        store.write_cert(b"cert pem")
        store.write_ca_bundle(b"bundle pem")
        assert stat.S_IMODE(store.cert_path.stat().st_mode) == 0o644
        assert stat.S_IMODE(store.ca_bundle_path.stat().st_mode) == 0o644

    def test_writes_overwrite_existing_content(self, store: CertStore) -> None:
        store.write_cert(b"v1")
        store.write_cert(b"v2")
        assert store.cert_path.read_bytes() == b"v2"
