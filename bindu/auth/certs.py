"""Certificate management for mTLS.

This module provides the CertificateInfrastructure class to handle:
- Certificate Authority (CA) initialization and management
- Agent certificate issuance based on DIDs
- Automatic certificate renewal
- Certificate revocation checking
"""

from __future__ import annotations

import datetime
import ipaddress
from pathlib import Path
from typing import Optional, List, Union, TYPE_CHECKING
import ssl

if TYPE_CHECKING:
    pass

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.certs")


class CertificateManager:
    """Manages mTLS certificates for an agent.

    Handles the lifecycle of the agent's identity certificate:
    - Generation of private keys
    - Creation of Certificate Signing Requests (CSR)
    - Interaction with a local or remote CA
    - Storage of certificates and keys
    """

    def __init__(
        self,
        cert_dir: Union[str, Path],
        ca_manager: Optional["CertificateAuthority"] = None,
    ):
        """Initialize certificate manager.

        Args:
            cert_dir: Directory to store certificates and keys
            ca_manager: Optional local CA manager (for self-hosted/dev setups)
        """
        self.cert_dir = Path(cert_dir)
        self.ca_manager = ca_manager

        # Define paths
        self.ca_cert_path = self.cert_dir / "ca.crt"
        self.key_path = self.cert_dir / "agent.key"
        self.cert_path = self.cert_dir / "agent.crt"

        # Ensure directory exists
        self.cert_dir.mkdir(parents=True, exist_ok=True)

    def ensure_certificate(
        self,
        did: str,
        dns_names: Optional[List[str]] = None,
        ip_addresses: Optional[List[str]] = None,
    ) -> bool:
        """Ensure valid certificate exists for the agent.

        If no certificate exists or it is expired/invalid, a new one is generated.

        Args:
            did: Agent's DID (used as Common Name)
            dns_names: List of subject alternative names (DNS)
            ip_addresses: List of subject alternative names (IP)

        Returns:
            True if certificate is valid and ready to use
        """
        if not self._check_certificate_validity():
            logger.info(
                f"Certificate missing or invalid for {did}, generating new one..."
            )
            return self._issue_new_certificate(did, dns_names, ip_addresses)

        return True

    def _check_certificate_validity(self) -> bool:
        """Check if current certificate is valid and not expiring soon."""
        if not (self.cert_path.exists() and self.key_path.exists()):
            return False

        try:
            with open(self.cert_path, "rb") as f:
                cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data)

            # Check expiry (renew if < 30 days remaining)
            now = datetime.datetime.now(datetime.timezone.utc)
            if cert.not_valid_after_utc < now + datetime.timedelta(days=30):
                logger.warning(
                    f"Certificate expiring soon (valid until {cert.not_valid_after_utc}), renewing..."
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking certificate validity: {e}")
            return False

    def _issue_new_certificate(
        self,
        did: str,
        dns_names: Optional[List[str]] = None,
        ip_addresses: Optional[List[str]] = None,
    ) -> bool:
        """Generate key and CSR, then get it signed."""
        try:
            # 1. Generate Private Key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Save Private Key
            with open(self.key_path, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

            # 2. Generate CSR
            csr_builder = x509.CertificateSigningRequestBuilder().subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, did),
                        x509.NameAttribute(
                            NameOID.ORGANIZATION_NAME, "Bindu Network Agent"
                        ),
                    ]
                )
            )

            # Add SANs
            san_list = []
            if dns_names:
                for name in dns_names:
                    san_list.append(x509.DNSName(name))
            if ip_addresses:
                for ip in ip_addresses:
                    san_list.append(x509.IPAddress(ipaddress.ip_address(ip)))

            # Always add localhost and 127.0.0.1 for local testing
            san_list.append(x509.DNSName("localhost"))
            san_list.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))

            if san_list:
                csr_builder = csr_builder.add_extension(
                    x509.SubjectAlternativeName(san_list),
                    critical=False,
                )

            csr = csr_builder.sign(private_key, hashes.SHA256())

            # 3. Sign with CA
            if self.ca_manager:
                # Use local CA
                cert = self.ca_manager.sign_csr(csr)

                # Save Certificate
                with open(self.cert_path, "wb") as f:
                    f.write(cert.public_bytes(serialization.Encoding.PEM))

                # Ensure CA cert is also present
                if not self.ca_cert_path.exists():
                    with open(self.ca_cert_path, "wb") as f:
                        f.write(
                            self.ca_manager.ca_cert.public_bytes(
                                serialization.Encoding.PEM
                            )
                        )

                logger.info(f"✅ Certificate issued successfully for {did}")
                return True
            else:
                logger.error("No CA manager available to sign certificate")
                return False

        except Exception as e:
            logger.error(f"Failed to issue certificate: {e}")
            return False

    def get_ssl_context(self) -> "ssl.SSLContext":
        """Create SSL context from stored certificates for uvicorn/aiohttp."""
        import ssl

        if not (
            self.cert_path.exists()
            and self.key_path.exists()
            and self.ca_cert_path.exists()
        ):
            raise FileNotFoundError(
                "Certificates not found. Run ensure_certificate() first."
            )

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.load_verify_locations(cafile=str(self.ca_cert_path))
        ssl_context.load_cert_chain(
            certfile=str(self.cert_path), keyfile=str(self.key_path)
        )

        return ssl_context


class CertificateAuthority:
    """Simple internal Certificate Authority for generating and signing certs."""

    def __init__(self, ca_dir: Union[str, Path]):
        """Initialize the Certificate Authority.

        Args:
            ca_dir: Directory where the CA certificate and key are stored.
        """
        self.ca_dir = Path(ca_dir)
        self.ca_dir.mkdir(parents=True, exist_ok=True)

        self.ca_key_path = self.ca_dir / "root_ca.key"
        self.ca_cert_path = self.ca_dir / "root_ca.crt"

        self.ca_key = None
        self.ca_cert = None

        self._load_or_create_ca()

    def _load_or_create_ca(self):
        """Load existing CA or create a new one."""
        if self.ca_key_path.exists() and self.ca_cert_path.exists():
            # Load existing
            try:
                with open(self.ca_key_path, "rb") as f:
                    self.ca_key = serialization.load_pem_private_key(
                        f.read(), password=None
                    )
                with open(self.ca_cert_path, "rb") as f:
                    self.ca_cert = x509.load_pem_x509_certificate(f.read())
                logger.info("Loaded existing Root CA")
            except Exception as e:
                logger.error(f"Failed to load CA, recreating: {e}")
                self._create_new_ca()
        else:
            self._create_new_ca()

    def _create_new_ca(self):
        """Generate a new self-signed Root CA."""
        logger.info("Generating new Root CA...")
        self.ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "Bindu Network Root CA"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Bindu Network"),
            ]
        )

        self.ca_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=3650)
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .sign(self.ca_key, hashes.SHA256())
        )

        # Save to disk
        with open(self.ca_key_path, "wb") as f:
            f.write(
                self.ca_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        with open(self.ca_cert_path, "wb") as f:
            f.write(self.ca_cert.public_bytes(serialization.Encoding.PEM))

        logger.info("✅ New Root CA generated")

    def sign_csr(self, csr: x509.CertificateSigningRequest) -> x509.Certificate:
        """Sign a CSR and issue a certificate."""
        if not self.ca_cert or not self.ca_key:
            raise RuntimeError("CA not initialized")

        # Verify CSR signature
        if not csr.is_signature_valid:
            raise ValueError("Invalid CSR signature")

        builder = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(self.ca_cert.subject)
            .public_key(csr.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(
                datetime.datetime.now(datetime.timezone.utc)
                + datetime.timedelta(days=365)
            )
        )

        # Copy extensions from CSR (SANs are important)
        for extension in csr.extensions:
            builder = builder.add_extension(extension.value, extension.critical)

        # Add Extended Key Usage for both Client and Server Auth
        builder = builder.add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]
            ),
            critical=False,
        )

        return builder.sign(self.ca_key, hashes.SHA256())

    def revoke_certificate(
        self, serial_number: int, reason: Optional[x509.ReasonFlags] = None
    ) -> None:
        """Revoke a certificate by serial number."""
        # In a real CA, persist this revocation state
        # For this implementation, we load/save a simple JSON or pickle,
        # but for simplicity we'll regenerate the CRL from memory if the process is alive,
        # or just rely on the CRL file being updated.

        # Load existing CRL if possible to append? No, standard is to rebuild CRL from database.
        # We will use a simple text file to track revoked serials for persistence.
        revocation_file = self.ca_dir / "revoked.txt"

        with open(revocation_file, "a") as f:
            f.write(f"{serial_number}\n")

        logger.info(f"Revoked certificate serial: {serial_number}")
        self.generate_crl()

    def generate_crl(self) -> x509.CertificateRevocationList:
        """Generate a Certificate Revocation List (CRL)."""
        if not self.ca_cert or not self.ca_key:
            raise RuntimeError("CA not initialized")

        builder = x509.CertificateRevocationListBuilder()
        builder = builder.issuer_name(self.ca_cert.subject)
        builder = builder.last_update(datetime.datetime.now(datetime.timezone.utc))
        builder = builder.next_update(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        )

        revocation_file = self.ca_dir / "revoked.txt"
        if revocation_file.exists():
            with open(revocation_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            serial = int(line.strip())
                            builder = builder.add_revoked_certificate(
                                x509.RevokedCertificateBuilder()
                                .serial_number(serial)
                                .revocation_date(
                                    datetime.datetime.now(datetime.timezone.utc)
                                )
                                .build()
                            )
                        except ValueError:
                            continue

        crl = builder.sign(private_key=self.ca_key, algorithm=hashes.SHA256())

        with open(self.ca_dir / "crl.pem", "wb") as f:
            f.write(crl.public_bytes(serialization.Encoding.PEM))

        return crl
