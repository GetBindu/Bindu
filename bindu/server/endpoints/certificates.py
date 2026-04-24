"""Certificate lifecycle endpoints for mTLS support.

Handles /issue, /renew, and /revoke operations tied to Agent DIDs.
Certificates are signed by the local CA and bound to Hydra OAuth2 clients
via RFC 8705 (certificate-bound access tokens).
"""

from __future__ import annotations as _annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote

import aiohttp
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu.auth.hydra.client import HydraClient
from bindu.common.protocol.types import CertificateData
from bindu.server.storage.schema import (
    agent_certificates_table,
    certificate_audit_log_table,
)
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.endpoints.certificates")


class CertificateNotFoundError(ValueError):
    """Raised when a certificate is not found in storage."""


class CertificateBindingError(RuntimeError):
    """Raised when Hydra certificate binding or unbinding fails."""


def _get_cert_ttl_hours() -> int:
    """Get certificate TTL from settings with a safe fallback."""
    return getattr(getattr(app_settings, "mtls", None), "cert_ttl_hours", 24)


def _get_certs_dir() -> Path:
    """Get certificate directory from settings with a safe fallback."""
    certs_dir = getattr(
        getattr(app_settings, "mtls", None),
        "certs_dir",
        "~/.bindu/certs",
    )
    return Path(certs_dir).expanduser()

# Default certificate TTL — 24 hours as per ADR


# -----------------------------------------------------------------------------
# Certificate utilities
# -----------------------------------------------------------------------------


def compute_sha256_fingerprint(cert_pem: str) -> str:
    """Compute SHA-256 fingerprint of a PEM-encoded certificate.

    Args:
        cert_pem: PEM-encoded certificate string

    Returns:
        Hex-encoded SHA-256 fingerprint
    """
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    return cert.fingerprint(hashes.SHA256()).hex()


def load_or_create_local_ca() -> tuple:
    """Load the local CA key+cert from ~/.bindu/certs/ or create on first run.

    Returns:
        Tuple of (ca_key, ca_cert)
    """
    certs_dir = _get_certs_dir()
    certs_dir.mkdir(parents=True, exist_ok=True)

    ca_key_path = certs_dir / "ca.key"
    ca_cert_path = certs_dir / "ca.crt"

    if ca_key_path.exists() and ca_cert_path.exists():
        with open(ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())
        logger.debug(f"Loaded existing local CA from {certs_dir}")
        return ca_key, ca_cert

    # First run — generate a new local Root CA
    logger.info(f"Generating local Root CA in {certs_dir} ...")
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Bindu Local CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Bindu"),
        ]
    )

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    with open(ca_key_path, "wb") as f:
        f.write(
            ca_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
    with open(ca_cert_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    logger.info(f"Local Root CA generated and saved to {certs_dir}")
    return ca_key, ca_cert


def sign_csr(csr_pem: str) -> str:
    """Sign a CSR with the local CA and return the signed certificate PEM.

    Args:
        csr_pem: PEM-encoded Certificate Signing Request

    Returns:
        PEM-encoded signed certificate
    """
    ca_key, ca_cert = load_or_create_local_ca()
    csr = x509.load_pem_x509_csr(csr_pem.encode())

    cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(
            datetime.now(timezone.utc) + timedelta(hours=_get_cert_ttl_hours())
        )
        .sign(ca_key, hashes.SHA256())
    )

    return cert.public_bytes(serialization.Encoding.PEM).decode()


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------


async def _bind_certificate(
    hydra_client: HydraClient,
    cert_fingerprint: str,
    agent_did: str,
) -> None:
    """Bind a certificate fingerprint to Hydra OAuth2 client (RFC 8705).

    Args:
        hydra_client: Initialised Hydra client
        cert_fingerprint: SHA-256 fingerprint to bind
        agent_did: Agent DID used as OAuth2 client_id
    """
    encoded_did = quote(agent_did, safe="")
    payload = {
        "client_id": agent_did,
        "jwks": {
            "keys": [
                {
                    "use": "sig",
                    "kty": "RSA",
                    "x5t#S256": cert_fingerprint,
                }
            ]
        },
    }
    try:
        response = await hydra_client._http_client.put(
            f"/admin/clients/{encoded_did}", json=payload
        )
        if response.status not in (200, 201):
            error_text = await response.text()
            raise CertificateBindingError(
                f"Failed to bind certificate to Hydra client: {error_text}"
            )
        logger.debug(
            f"Certificate bound to Hydra client: did={agent_did}, "
            f"fingerprint={cert_fingerprint[:16]}..."
        )
    except (aiohttp.ClientError, CertificateBindingError) as error:
        logger.error(f"Failed to bind agent certificate: {error}")
        raise CertificateBindingError(f"Certificate binding failed: {str(error)}")


async def _unbind_certificate(
    hydra_client: HydraClient,
    agent_did: str,
) -> None:
    """Remove certificate binding from Hydra OAuth2 client (used on revocation).

    Args:
        hydra_client: Initialised Hydra client
        agent_did: Agent DID used as OAuth2 client_id
    """
    encoded_did = quote(agent_did, safe="")
    payload = {"client_id": agent_did, "jwks": {"keys": []}}
    try:
        response = await hydra_client._http_client.put(
            f"/admin/clients/{encoded_did}", json=payload
        )
        if response.status not in (200, 201):
            error_text = await response.text()
            raise CertificateBindingError(
                f"Failed to unbind certificate from Hydra client: {error_text}"
            )
        logger.debug(f"Certificate unbound from Hydra client: did={agent_did}")
    except (aiohttp.ClientError, CertificateBindingError) as error:
        logger.error(f"Failed to unbind agent certificate: {error}")
        raise CertificateBindingError(f"Certificate unbinding failed: {str(error)}")


async def _write_audit_log(
    conn: AsyncConnection,
    event_type: str,
    agent_did: str,
    cert_fingerprint: str,
    performed_by: str | None = None,
    event_data: Dict[str, Any] | None = None,
) -> None:
    """Write an immutable entry to the certificate audit log.

    Args:
        conn: Active async DB connection
        event_type: One of issued | renewed | revoked
        agent_did: DID of the agent
        cert_fingerprint: SHA-256 fingerprint of the certificate
        performed_by: DID or system identifier of who performed the action
        event_data: Additional context to store with the event
    """
    await conn.execute(
        certificate_audit_log_table.insert().values(
            id=uuid.uuid4(),
            event_type=event_type,
            agent_did=agent_did,
            cert_fingerprint=cert_fingerprint,
            performed_by=performed_by or "system",
            event_data=event_data or {},
        )
    )


# -----------------------------------------------------------------------------
# Authorization helpers
# -----------------------------------------------------------------------------


def _get_caller_did(request: Request) -> str | None:
    """Extract the caller's DID from request state (set by auth middleware).

    Returns:
        The authenticated agent DID, or None if unauthenticated.
    """
    return getattr(request.state, "agent_did", None)


def _authorize_agent_did(
    caller_did: str | None,
    requested_did: str,
) -> JSONResponse | None:
    """Check that the authenticated caller owns the requested agent_did.

    Returns a JSONResponse error if unauthorized, or None if authorized.

    Args:
        caller_did: DID extracted from the authenticated request.
        requested_did: DID supplied in the request body.

    Returns:
        JSONResponse with 401/403 if unauthorized, None if authorized.
    """
    if caller_did is None:
        return JSONResponse(
            {"error": "Authentication required"},
            status_code=401,
        )
    if caller_did != requested_did:
        logger.warning(
            f"Authorization denied: caller={caller_did} "
            f"attempted to manage certificates for {requested_did}"
        )
        return JSONResponse(
            {"error": "Forbidden: cannot manage certificates for another agent"},
            status_code=403,
        )
    return None


# -----------------------------------------------------------------------------
# Core certificate lifecycle logic
# -----------------------------------------------------------------------------


async def issue_certificate(
    agent_did: str,
    csr_pem: str,
    conn: AsyncConnection,
    hydra_client: HydraClient,
) -> CertificateData:
    """Issue a new mTLS certificate for an agent DID.

    Signs the CSR with the local CA, persists to DB, and binds to Hydra
    for RFC 8705 token binding.

    Args:
        agent_did: DID of the requesting agent
        csr_pem: PEM-encoded Certificate Signing Request
        conn: Active async DB connection
        hydra_client: Initialised Hydra client

    Returns:
        CertificateData with the signed cert and metadata
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=_get_cert_ttl_hours())

    cert_pem = sign_csr(csr_pem)
    fingerprint = compute_sha256_fingerprint(cert_pem)

    await conn.execute(
        agent_certificates_table.insert().values(
            id=uuid.uuid4(),
            agent_did=agent_did,
            cert_fingerprint=fingerprint,
            status="active",
            issued_at=now,
            expires_at=expires_at,
        )
    )

    await _bind_certificate(hydra_client, fingerprint, agent_did)

    await _write_audit_log(
        conn,
        "issued",
        agent_did,
        fingerprint,
        event_data={"expires_at": expires_at.isoformat()},
    )

    logger.info(
        f"Certificate issued: did={agent_did}, fingerprint={fingerprint[:16]}..."
    )

    return CertificateData(
        certificate_pem=cert_pem,
        cert_fingerprint=fingerprint,
        status="issued",
        issued_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        agent_did=agent_did,
    )


async def renew_certificate(
    agent_did: str,
    csr_pem: str,
    current_fingerprint: str,
    conn: AsyncConnection,
    hydra_client: HydraClient,
) -> CertificateData:
    """Renew an mTLS certificate before expiry.

    Args:
        agent_did: DID of the agent
        csr_pem: PEM-encoded CSR for the new certificate
        current_fingerprint: Fingerprint of the currently active certificate
        conn: Active async DB connection
        hydra_client: Initialised Hydra client

    Returns:
        CertificateData for the new certificate

    Raises:
        CertificateNotFoundError: If no active certificate matches the provided fingerprint
    """
    result = await conn.execute(
        select(agent_certificates_table).where(
            agent_certificates_table.c.cert_fingerprint == current_fingerprint,
            agent_certificates_table.c.agent_did == agent_did,
            agent_certificates_table.c.status == "active",
        )
    )
    existing = result.fetchone()
    if not existing:
        raise CertificateNotFoundError(
            f"No active certificate found for did={agent_did} "
            f"with fingerprint={current_fingerprint[:16]}..."
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=_get_cert_ttl_hours())
    new_cert_pem = sign_csr(csr_pem)
    new_fingerprint = compute_sha256_fingerprint(new_cert_pem)

    # Mark old cert as expired
    await conn.execute(
        update(agent_certificates_table)
        .where(agent_certificates_table.c.cert_fingerprint == current_fingerprint)
        .values(status="expired")
    )

    # Insert new cert
    await conn.execute(
        agent_certificates_table.insert().values(
            id=uuid.uuid4(),
            agent_did=agent_did,
            cert_fingerprint=new_fingerprint,
            status="active",
            issued_at=now,
            expires_at=expires_at,
        )
    )

    await _bind_certificate(hydra_client, new_fingerprint, agent_did)

    await _write_audit_log(
        conn,
        "renewed",
        agent_did,
        new_fingerprint,
        event_data={
            "previous_fingerprint": current_fingerprint,
            "expires_at": expires_at.isoformat(),
        },
    )

    logger.info(
        f"Certificate renewed: did={agent_did}, "
        f"new_fingerprint={new_fingerprint[:16]}..."
    )

    return CertificateData(
        certificate_pem=new_cert_pem,
        cert_fingerprint=new_fingerprint,
        status="active",
        issued_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        agent_did=agent_did,
    )


async def revoke_certificate(
    agent_did: str,
    cert_fingerprint: str,
    conn: AsyncConnection,
    hydra_client: HydraClient,
    reason: str | None = None,
) -> None:
    """Revoke an mTLS certificate immediately.

    Args:
        agent_did: DID of the agent
        cert_fingerprint: SHA-256 fingerprint of the certificate to revoke
        conn: Active async DB connection
        hydra_client: Initialised Hydra client
        reason: Optional revocation reason for the audit log

    Raises:
        CertificateNotFoundError: If the certificate is not found
    """
    result = await conn.execute(
        update(agent_certificates_table)
        .where(
            agent_certificates_table.c.cert_fingerprint == cert_fingerprint,
            agent_certificates_table.c.agent_did == agent_did,
        )
        .values(status="revoked")
        .returning(agent_certificates_table.c.id)
    )

    if not result.fetchone():
        raise CertificateNotFoundError(
            f"Certificate not found: did={agent_did}, "
            f"fingerprint={cert_fingerprint[:16]}..."
        )

    await _unbind_certificate(hydra_client, agent_did)

    await _write_audit_log(
        conn,
        "revoked",
        agent_did,
        cert_fingerprint,
        event_data={"reason": reason or "not specified"},
    )

    logger.info(
        f"Certificate revoked: did={agent_did}, "
        f"fingerprint={cert_fingerprint[:16]}..."
    )


# -----------------------------------------------------------------------------
# HTTP endpoint handlers (Starlette routes)
# -----------------------------------------------------------------------------


async def issue_certificate_endpoint(app: Any, request: Request) -> JSONResponse:
    """Handle POST /api/v1/certificates/issue."""
    try:
        body = await request.json()
        agent_did = body.get("agent_did")
        csr_pem = body.get("csr")

        if not agent_did or not csr_pem:
            return JSONResponse(
                {"error": "agent_did and csr are required"},
                status_code=400,
            )

        if auth_error := _authorize_agent_did(_get_caller_did(request), agent_did):
            return auth_error

        async with app._storage.connection() as conn:
            hydra_client = HydraClient(admin_url=app_settings.hydra.admin_url)
            result = await issue_certificate(agent_did, csr_pem, conn, hydra_client)

        return JSONResponse(dict(result), status_code=201)

    except CertificateBindingError:
        logger.error("Certificate binding failure during issuance")
        return JSONResponse({"error": "Certificate operation failed"}, status_code=502)
    except Exception as e:
        logger.error(f"Certificate issuance failed: {e}")
        return JSONResponse({"error": "Certificate issuance failed"}, status_code=500)


async def renew_certificate_endpoint(app: Any, request: Request) -> JSONResponse:
    """Handle POST /api/v1/certificates/renew."""
    try:
        body = await request.json()
        agent_did = body.get("agent_did")
        csr_pem = body.get("csr")
        current_fingerprint = body.get("current_fingerprint")

        if not all([agent_did, csr_pem, current_fingerprint]):
            return JSONResponse(
                {"error": "agent_did, csr, and current_fingerprint are required"},
                status_code=400,
            )

        if auth_error := _authorize_agent_did(_get_caller_did(request), agent_did):
            return auth_error

        async with app._storage.connection() as conn:
            hydra_client = HydraClient(admin_url=app_settings.hydra.admin_url)
            result = await renew_certificate(
                agent_did, csr_pem, current_fingerprint, conn, hydra_client
            )

        return JSONResponse(dict(result), status_code=200)

    except CertificateNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except CertificateBindingError:
        logger.error("Certificate binding failure during renewal")
        return JSONResponse({"error": "Certificate operation failed"}, status_code=502)
    except Exception as e:
        logger.error(f"Certificate renewal failed: {e}")
        return JSONResponse({"error": "Certificate renewal failed"}, status_code=500)


async def revoke_certificate_endpoint(app: Any, request: Request) -> JSONResponse:
    """Handle POST /api/v1/certificates/revoke."""
    try:
        body = await request.json()
        agent_did = body.get("agent_did")
        cert_fingerprint = body.get("cert_fingerprint")
        reason = body.get("reason")

        if not agent_did or not cert_fingerprint:
            return JSONResponse(
                {"error": "agent_did and cert_fingerprint are required"},
                status_code=400,
            )

        if auth_error := _authorize_agent_did(_get_caller_did(request), agent_did):
            return auth_error

        async with app._storage.connection() as conn:
            hydra_client = HydraClient(admin_url=app_settings.hydra.admin_url)
            await revoke_certificate(
                agent_did, cert_fingerprint, conn, hydra_client, reason
            )

        return JSONResponse({"status": "revoked"}, status_code=200)

    except CertificateNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except CertificateBindingError:
        logger.error("Certificate binding failure during revocation")
        return JSONResponse({"error": "Certificate operation failed"}, status_code=502)
    except Exception as e:
        logger.error(f"Certificate revocation failed: {e}")
        return JSONResponse({"error": "Certificate revocation failed"}, status_code=500)
