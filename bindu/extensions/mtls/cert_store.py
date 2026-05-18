# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""On-disk storage for X.509 certificates, keys, and the CA bundle.

Pure leaf logic — no network, no orchestration. The store owns path resolution
inside the agent's PKI directory, atomic writes with POSIX permission bits, and
the EC keypair / CSR / fingerprint helpers used by the rest of the mTLS
extension.

Files written by this module
----------------------------
``{pki_dir}/tls_key.pem``     EC P-256 private key (mode 0o600)
``{pki_dir}/tls_cert.pem``    Agent X.509 certificate (mode 0o644)
``{pki_dir}/ca_bundle.pem``   Intermediate + root chain (mode 0o644)
``{pki_dir}/tls.csr``         Last CSR sent to step-ca (mode 0o644, debug only)
"""

from __future__ import annotations

import os
import platform

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.mtls.cert_store")


class CertStore:
    """File-backed store for an agent's mTLS material.

    Instances are bound to a single PKI directory — typically the same directory
    the DID extension already uses, so cert files live next to the Ed25519
    keypair. Callers are responsible for creating the directory before
    constructing the store.
    """

    def __init__(self, pki_dir: Path):
        """Bind the store to a PKI directory.

        Args:
            pki_dir: Directory that already exists and is writable by the agent
                process. The DID extension creates this directory on startup;
                the mTLS extension reuses it.
        """
        self.pki_dir = Path(pki_dir)
        cfg = app_settings.mtls
        self.cert_path = self.pki_dir / cfg.cert_filename
        self.key_path = self.pki_dir / cfg.key_filename
        self.ca_bundle_path = self.pki_dir / cfg.ca_bundle_filename
        self.csr_path = self.pki_dir / cfg.csr_filename

    # ------------------------------------------------------------------
    # Existence checks
    # ------------------------------------------------------------------

    def has_cert(self) -> bool:
        """Return True when both the cert and its private key are on disk."""
        return self.cert_path.is_file() and self.key_path.is_file()

    def has_ca_bundle(self) -> bool:
        """Return True when the CA bundle PEM is on disk."""
        return self.ca_bundle_path.is_file()

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def read_cert(self) -> bytes:
        """Return the cert PEM bytes. Raises FileNotFoundError if missing."""
        return self.cert_path.read_bytes()

    def read_key(self) -> bytes:
        """Return the private-key PEM bytes. Raises FileNotFoundError if missing."""
        return self.key_path.read_bytes()

    def read_ca_bundle(self) -> bytes:
        """Return the CA-bundle PEM bytes. Raises FileNotFoundError if missing."""
        return self.ca_bundle_path.read_bytes()

    # ------------------------------------------------------------------
    # Write helpers — atomic, POSIX-aware
    # ------------------------------------------------------------------

    def write_cert(self, cert_pem: bytes) -> None:
        """Write the agent cert PEM with mode 0o644."""
        _write_bytes(self.cert_path, cert_pem, mode=0o644)

    def write_key(self, key_pem: bytes) -> None:
        """Write the private-key PEM with mode 0o600 (owner-only on POSIX)."""
        _write_bytes(self.key_path, key_pem, mode=0o600)

    def write_ca_bundle(self, bundle_pem: bytes) -> None:
        """Write the CA bundle PEM with mode 0o644."""
        _write_bytes(self.ca_bundle_path, bundle_pem, mode=0o644)

    def write_csr(self, csr_pem: bytes) -> None:
        """Persist the most recent CSR for debugging."""
        _write_bytes(self.csr_path, csr_pem, mode=0o644)

    # ------------------------------------------------------------------
    # Keypair + CSR generation
    # ------------------------------------------------------------------

    def generate_keypair(self) -> Tuple[ec.EllipticCurvePrivateKey, bytes]:
        """Generate a fresh EC P-256 keypair and persist the private key.

        Returns:
            Tuple of (private-key object, PEM bytes) so callers can build a CSR
            without re-reading from disk.
        """
        private_key = ec.generate_private_key(ec.SECP256R1())
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.write_key(key_pem)
        return private_key, key_pem

    def load_private_key(self) -> ec.EllipticCurvePrivateKey:
        """Load the EC private key from disk. Raises FileNotFoundError if missing."""
        key_pem = self.read_key()
        key = serialization.load_pem_private_key(key_pem, password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey):
            raise TypeError(
                f"Expected EC private key in {self.key_path}, got {type(key).__name__}"
            )
        return key

    def build_csr(
        self,
        private_key: ec.EllipticCurvePrivateKey,
        agent_did: str,
        agent_url: Optional[str] = None,
    ) -> bytes:
        """Build a CSR with the agent DID in CN and a URI SAN.

        The CN carries the DID for legacy peers that authenticate by subject;
        modern peers should rely on the URI SAN. When ``agent_url`` is provided
        and parseable, its hostname is also added as a DNS SAN so off-the-shelf
        TLS clients can verify by hostname.

        Args:
            private_key: EC private key returned by ``generate_keypair``.
            agent_did: Fully-qualified DID, e.g. ``did:bindu:author:name:id``.
            agent_url: Optional agent base URL, e.g. ``https://agent.example.com``.

        Returns:
            PEM-encoded CSR bytes. The caller is responsible for sending it to
            step-ca; this method does not perform I/O.
        """
        san_entries: list[x509.GeneralName] = [
            x509.UniformResourceIdentifier(agent_did)
        ]
        if agent_url:
            host = _hostname_from_url(agent_url)
            if host:
                san_entries.append(x509.DNSName(host))

        builder = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, _shorten_cn(agent_did)),
                    ]
                )
            )
            .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        )
        csr = builder.sign(private_key, hashes.SHA256())
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)
        self.write_csr(csr_pem)
        return csr_pem

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def get_cert_expiry(self) -> Optional[datetime]:
        """Return the cert's notAfter as a tz-aware UTC datetime, or None.

        Returns None when the cert file is missing or unparseable. Callers
        should treat None as "renewal needed" rather than raising.
        """
        if not self.cert_path.is_file():
            return None
        try:
            cert = x509.load_pem_x509_certificate(self.cert_path.read_bytes())
        except ValueError as exc:
            logger.warning("Could not parse cert at %s: %s", self.cert_path, exc)
            return None
        # ``not_valid_after_utc`` was added in cryptography 42.0; fall back for older.
        not_after = getattr(cert, "not_valid_after_utc", None)
        if not_after is None:
            not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
        return not_after

    def is_renewal_due(self, renew_before_hours: int) -> bool:
        """Return True when the cert is missing, unparseable, or near expiry."""
        expiry = self.get_cert_expiry()
        if expiry is None:
            return True
        remaining = expiry - datetime.now(timezone.utc)
        return remaining.total_seconds() < renew_before_hours * 3600

    def get_cert_fingerprint(self) -> Optional[str]:
        """Return the SHA-256 fingerprint of the cert as a colon-separated hex string.

        Suitable for ``AgentTrust.certificate_fingerprint``. Returns None when
        the cert file is missing.
        """
        if not self.cert_path.is_file():
            return None
        cert = x509.load_pem_x509_certificate(self.cert_path.read_bytes())
        digest = cert.fingerprint(hashes.SHA256())
        return ":".join(f"{b:02x}" for b in digest)


# ----------------------------------------------------------------------
# Private helpers
# ----------------------------------------------------------------------


def _write_bytes(path: Path, data: bytes, *, mode: int) -> None:
    """Write ``data`` to ``path`` with the requested POSIX mode.

    Mirrors the DID extension's approach: on POSIX, use ``os.open`` so the
    permission bits are set atomically at creation; on Windows, fall back to
    a plain write because the filesystem ignores POSIX modes anyway.
    """
    if platform.system() == "Windows":
        path.write_bytes(data)
        return
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def _hostname_from_url(url: str) -> Optional[str]:
    """Extract the hostname from a URL, returning None on parse failure."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    return parsed.hostname


# X.509 CommonName is capped at 64 bytes by RFC 5280. Real Bindu DIDs of
# the shape ``did:bindu:{author}:{name}:{agent_id}`` routinely exceed
# that — an email author + a meaningful agent name + a 36-char UUID
# easily clears 80 chars. The full DID still goes in the URI SAN (which
# has no length cap), and step-ca's OIDC provisioner overrides whatever
# we put in CN with the token's ``sub`` claim anyway, so the CN we send
# is largely cosmetic. We use the last colon-delimited segment (the
# agent UUID for the canonical DID format) as the CN — short, stable,
# unique, and human-readable.
_CN_MAX_LEN = 64


def _shorten_cn(agent_did: str) -> str:
    """Produce a CN value ≤ 64 bytes from any DID.

    Tries the last ``:``-delimited segment first (the agent UUID under the
    canonical ``did:bindu:author:name:id`` shape). Falls back to a hard
    truncation for DIDs whose tail segment is itself >64 bytes — both
    pathways yield a stable derivative of the input.
    """
    last_segment = agent_did.rsplit(":", 1)[-1]
    if 0 < len(last_segment) <= _CN_MAX_LEN:
        return last_segment
    return agent_did[:_CN_MAX_LEN]
