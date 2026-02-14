"""Zero-Trust Middleware for mTLS Certificate Validation.

This middleware extracts the client certificate from the connection
and validates it against the trust policy.
"""

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from bindu.utils.logging import get_logger
from bindu.settings import app_settings
from pathlib import Path

logger = get_logger("bindu.server.middleware.mtls")


class MTLSMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce and validate client certificates."""

    def __init__(self, app: ASGIApp):
        """Initialize the mTLS middleware.

        Args:
            app: The ASGI application.
        """
        super().__init__(app)
        self.enabled = app_settings.security.mtls_enabled

    async def dispatch(self, request: Request, call_next):
        """Process request and validate client certificate."""
        # If mTLS is disabled, skip validation
        if not self.enabled:
            return await call_next(request)

        # Get transport information
        try:
            # Uvicorn/Starlette exposes SSL object in scope['extensions']['tls'] or scope['transport']
            # However, standard ASGI doesn't standardize this perfectly.
            # In Uvicorn with SSL, the transport info is available.
            transport = request.scope.get("transport")
            if not transport:
                logger.warning(
                    f"No transport information found in request scope. Keys: {list(request.scope.keys())}"
                )
                # Check for other potential locations
                if "extensions" in request.scope:
                    logger.info(f"Extensions: {request.scope['extensions']}")

                # If we are behind a reverse proxy that handles TLS, this might be expected,
                # but for direct mTLS it's an error.
                # For now, we assume direct connection if mTLS is enabled.
                pass

            # Extract client certificate
            # Note: This depends heavily on the ASGI server implementation.
            # Uvicorn exposes get_extra_info('ssl_object')
            # Try to get cert from ASGI TLS extension (supported by uvicorn/httptools/uvloop)
            cert = None
            tls_ext = request.scope.get("extensions", {}).get("tls", {})
            if "client_cert" in tls_ext:
                # client_cert is typically a list of PEM strings [client_cert, chain...]
                client_certs = tls_ext.get("client_cert")
                if client_certs:
                    # Load the first certificate (the client's)
                    pem_data = client_certs[0]
                    if isinstance(pem_data, str):
                        pem_data = pem_data.encode("utf-8")

                    try:
                        cert = x509.load_pem_x509_certificate(
                            pem_data, default_backend()
                        )
                        # We have the cert object directly
                    except Exception as e:
                        logger.error(
                            f"Failed to parse client certificate from TLS extension: {e}"
                        )
                        return await self._unauthorized("Invalid client certificate")
                else:
                    return await self._unauthorized("Client certificate required")

            else:
                # Fallback to Transport/SSL Object (standard uvicorn/h11)
                ssl_object = (
                    transport.get_extra_info("ssl_object") if transport else None
                )

                if not ssl_object:
                    # If mTLS is enabled, an SSL object is expected.
                    logger.warning(
                        "No SSL object found on connection and no TLS extension"
                    )
                    return await self._unauthorized("Client certificate required")

                cert_der = ssl_object.getpeercert(binary_form=True)
                if not cert_der:
                    logger.warning("No client certificate provided via SSL object")
                    return await self._unauthorized("Client certificate required")

                try:
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())
                except Exception as e:
                    logger.error(
                        f"Failed to parse client certificate from SSL object: {e}"
                    )
                    return await self._unauthorized("Invalid client certificate")

            # At this point, 'cert' should be an x509.Certificate object
            if not cert:
                logger.error("Certificate object could not be loaded by any method.")
                return await self._unauthorized("Client certificate required")

            # 1. Freshness Check
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
                logger.warning(
                    f"Client certificate expired or not yet valid: {cert.not_valid_after_utc}"
                )
                return await self._unauthorized("Client certificate expired or invalid")

            # Check if close to expiry (Anomaly/Warning)
            # if (cert.not_valid_after_utc - now).days < 30:
            #     logger.warning(f"Client certificate for {client_did} expires soon")

            # 2. Revocation Check (CRL)
            try:
                crl_path = Path(app_settings.security.cert_dir) / "ca" / "crl.pem"
                if crl_path.exists():
                    with open(crl_path, "rb") as f:
                        crl = x509.load_pem_x509_crl(f.read())

                    # Check if revoked
                    revoked_cert = crl.get_revoked_certificate_by_serial_number(
                        cert.serial_number
                    )
                    if revoked_cert:
                        logger.warning(
                            f"Client certificate serial {cert.serial_number} is revoked"
                        )
                        return await self._unauthorized("Client certificate revoked")
            except Exception as e:
                logger.error(f"Error checking CRL: {e}")
                # Fail-safe: If CRL check fails, do we deny?
                # For high security, yes. For reliability, maybe no.
                # Let's log error but proceed if it's just a file read error,
                # unless strict mode is enabled.

            # Validate Common Name (DID)
            cn_attributes = cert.subject.get_attributes_for_oid(
                x509.NameOID.COMMON_NAME
            )
            if not cn_attributes:
                return await self._unauthorized("Certificate missing Common Name")

            client_did = cn_attributes[0].value

            # 2. Pinning / Allowlist (Zero-Trust)
            # Only allow specific DIDs if configured
            # allowed_dids = app_settings.security.allowed_peers
            # if allowed_dids and client_did not in allowed_dids:
            #     logger.warning(f"Blocked connection from unallowed DID: {client_did}")
            #     return await self._unauthorized("Peer not allowed")

            # Attach DID to request state for downstream use
            request.state.client_did = client_did
            request.state.mtls_verified = True

            logger.debug(f"mTLS authenticated client: {client_did}")

        except Exception as e:
            logger.error(f"mTLS validation error: {e}")
            return await self._unauthorized("Certificate validation failed")

        return await call_next(request)

    async def _unauthorized(self, message: str) -> JSONResponse:
        """Return 401 Unauthorized response."""
        return JSONResponse(
            {"error": "unauthorized", "detail": message}, status_code=401
        )
