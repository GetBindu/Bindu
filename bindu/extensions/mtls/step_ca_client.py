# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""HTTP client for Smallstep step-ca.

This module owns the on-the-wire contract with the CA. The cert store handles
disk; this client handles the network. ``MTLSAgentExtension`` orchestrates the
two.

The contract follows the step-ca REST API as described in
``docs/MTLS_DEPLOYMENT_GUIDE.md`` section 8:

* ``GET {ca_root_url}`` — fetch the trust-anchor PEM (no auth).
* ``POST {ca_url}/1.0/sign`` — body ``{"csr", "ott", "notAfter"}``; the ``ott``
  is a Hydra-issued OIDC token validated by step-ca's OIDC provisioner.
  Response: ``{"crt", "ca"}``.
* ``GET {ca_url}/health`` — returns 200 when step-ca is healthy.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple
from urllib.parse import urlparse

from bindu.settings import app_settings
from bindu.utils.http import AsyncHTTPClient
from bindu.utils.logging import get_logger

logger = get_logger("bindu.mtls.step_ca")


class StepCAError(RuntimeError):
    """Raised when step-ca returns an unexpected response shape or status."""


class StepCAClient:
    """Thin async wrapper around the step-ca REST API.

    The CA is shared infrastructure deployed at ``app_settings.mtls.ca_url``.
    Each agent talks to it twice per cert lifecycle: once to fetch the root
    bundle for peer verification, and once per renewal to sign a CSR.

    Two underlying ``AsyncHTTPClient`` instances are used because the root
    bundle is often served from a different host (a static well-known URL)
    than the signing API.
    """

    def __init__(
        self,
        ca_url: str | None = None,
        ca_root_url: str | None = None,
        provisioner: str | None = None,
        timeout: int | None = None,
        verify_ssl: bool | None = None,
        max_retries: int | None = None,
    ):
        """Configure the client.

        Each argument falls back to its ``MTLSSettings`` default when omitted,
        so production code can construct ``StepCAClient()`` with no args and
        tests can override individual fields.
        """
        cfg = app_settings.mtls
        self.ca_url = (ca_url if ca_url is not None else cfg.ca_url).rstrip("/")
        self.ca_root_url = ca_root_url if ca_root_url is not None else cfg.ca_root_url
        self.provisioner = (
            provisioner if provisioner is not None else cfg.ca_provisioner
        )
        self.timeout = timeout if timeout is not None else cfg.timeout
        self.verify_ssl = verify_ssl if verify_ssl is not None else cfg.verify_ssl
        self.max_retries = max_retries if max_retries is not None else cfg.max_retries

        self._api_client = AsyncHTTPClient(
            base_url=self.ca_url,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            max_retries=self.max_retries,
            default_headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        # The roots URL may live on a different host (e.g. a static CDN) than
        # the signing API, so it gets its own client. Splitting the URL into
        # base + path keeps the request shape consistent with the rest of the
        # codebase, which always passes an endpoint to ``AsyncHTTPClient``.
        parsed = urlparse(self.ca_root_url)
        self._roots_base = f"{parsed.scheme}://{parsed.netloc}"
        self._roots_path = parsed.path or "/roots.pem"
        self._roots_client = AsyncHTTPClient(
            base_url=self._roots_base,
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            max_retries=self.max_retries,
        )

    async def __aenter__(self) -> "StepCAClient":
        """Async context manager entry. Returns self for ``async with`` usage."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit. Closes underlying HTTP sessions."""
        await self.close()

    async def close(self) -> None:
        """Release both underlying HTTP sessions."""
        await self._api_client.close()
        await self._roots_client.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_root_ca(self) -> bytes:
        """Fetch the CA bundle PEM from ``ca_root_url``.

        Returns:
            PEM bytes containing the root + intermediate chain that agents
            should trust when verifying peers.

        Raises:
            StepCAError: when the response is not a PEM bundle.
        """
        logger.debug("Fetching CA bundle from %s", self.ca_root_url)
        response = await self._roots_client.get(self._roots_path)
        body = response._body if hasattr(response, "_body") else await response.read()
        if not body or b"BEGIN CERTIFICATE" not in body:
            raise StepCAError(
                f"CA bundle endpoint {self.ca_root_url} did not return a PEM payload"
            )
        return body

    async def sign_csr(
        self,
        csr_pem: bytes,
        oidc_token: str,
        ttl_hours: int | None = None,
    ) -> Tuple[bytes, bytes]:
        """Submit a CSR to step-ca and return the signed certificate.

        Args:
            csr_pem: PEM-encoded CSR produced by ``CertStore.build_csr``.
            oidc_token: A Hydra-issued OIDC token. step-ca's OIDC provisioner
                validates this against Hydra's JWKS endpoint to authorize the
                signing request.
            ttl_hours: Override for the requested cert lifetime. Defaults to
                ``MTLSSettings.cert_ttl_hours``. step-ca may clamp this to the
                provisioner's configured max.

        Returns:
            ``(cert_pem, chain_pem)`` — the agent cert and the intermediate
            chain. Callers concatenate the two when serving TLS.
        """
        ttl = ttl_hours if ttl_hours is not None else app_settings.mtls.cert_ttl_hours
        not_after = (datetime.now(timezone.utc) + timedelta(hours=ttl)).isoformat()
        body = {
            "csr": csr_pem.decode("ascii"),
            "ott": oidc_token,
            "notAfter": not_after,
        }
        logger.debug(
            "Signing CSR via %s/1.0/sign (notAfter=%s)", self.ca_url, not_after
        )
        response = await self._api_client.post(
            "/1.0/sign",
            json=body,
            headers={"Authorization": f"Bearer {oidc_token}"},
        )
        data = await response.json()
        if not isinstance(data, dict) or "crt" not in data or "ca" not in data:
            raise StepCAError(
                f"Unexpected sign response shape from step-ca: keys={list(data.keys()) if isinstance(data, dict) else type(data)}"
            )
        cert_pem = data["crt"].encode("ascii")
        chain_pem = data["ca"].encode("ascii")
        return cert_pem, chain_pem

    async def health_check(self) -> bool:
        """Return True when step-ca's ``/health`` endpoint reports OK.

        Never raises — connection errors are logged and treated as unhealthy
        so the renewal loop can skip a cycle rather than crash the agent.
        """
        try:
            response = await self._api_client.get("/health")
            return response.status == 200
        except Exception as exc:  # noqa: BLE001 - intentional broad catch
            logger.warning("step-ca health check at %s failed: %s", self.ca_url, exc)
            return False
