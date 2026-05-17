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

Scope for Phase 1 (this commit)
-------------------------------
- Class signature, dependency wiring, settings binding.
- Method signatures and docstrings so callers can program against the surface.

Method bodies arrive in Phase 2 once a step-ca instance is reachable from a
dev environment. Until then, every network call raises ``NotImplementedError``
so a misconfigured ``mtls.enabled = True`` fails loudly rather than silently
shipping an insecure agent.
"""

from __future__ import annotations

from typing import Tuple

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.mtls.step_ca")


class StepCAClient:
    """Thin async wrapper around the step-ca REST API.

    The CA is shared infrastructure deployed at ``app_settings.mtls.ca_url``.
    Each agent talks to it twice per cert lifecycle: once to fetch the root
    bundle for peer verification, and once per renewal to sign a CSR.
    """

    def __init__(
        self,
        ca_url: str | None = None,
        ca_root_url: str | None = None,
        provisioner: str | None = None,
        timeout: int | None = None,
        verify_ssl: bool | None = None,
    ):
        """Configure the client.

        Each argument falls back to its ``MTLSSettings`` default when omitted,
        so production code can construct ``StepCAClient()`` with no args and
        tests can override individual fields.
        """
        cfg = app_settings.mtls
        self.ca_url = ca_url if ca_url is not None else cfg.ca_url
        self.ca_root_url = ca_root_url if ca_root_url is not None else cfg.ca_root_url
        self.provisioner = (
            provisioner if provisioner is not None else cfg.ca_provisioner
        )
        self.timeout = timeout if timeout is not None else cfg.timeout
        self.verify_ssl = verify_ssl if verify_ssl is not None else cfg.verify_ssl

    # ------------------------------------------------------------------
    # Public API (bodies land in Phase 2)
    # ------------------------------------------------------------------

    async def fetch_root_ca(self) -> bytes:
        """Fetch the CA bundle PEM from ``ca_root_url``.

        Returns:
            PEM bytes containing the root + intermediate chain that agents
            should trust when verifying peers.

        Raises:
            NotImplementedError: until Phase 2 wires the HTTP call.
        """
        raise NotImplementedError(
            "StepCAClient.fetch_root_ca lands in Phase 2 of the mTLS rollout"
        )

    async def sign_csr(self, csr_pem: bytes, oidc_token: str) -> Tuple[bytes, bytes]:
        """Submit a CSR to step-ca and return the signed certificate.

        Args:
            csr_pem: PEM-encoded CSR produced by ``CertStore.build_csr``.
            oidc_token: A Hydra-issued OIDC token. step-ca's OIDC provisioner
                validates this against Hydra's JWKS endpoint to authorize the
                signing request.

        Returns:
            ``(cert_pem, chain_pem)`` — the agent cert and the intermediate
            chain. Callers concatenate the two when serving TLS.

        Raises:
            NotImplementedError: until Phase 2 wires the HTTP call.
        """
        raise NotImplementedError(
            "StepCAClient.sign_csr lands in Phase 2 of the mTLS rollout"
        )

    async def health_check(self) -> bool:
        """Return True when step-ca's ``/health`` endpoint reports OK.

        Used by the renewal loop to skip a renewal cycle when the CA is
        unreachable rather than thrashing on a failing endpoint.

        Raises:
            NotImplementedError: until Phase 2 wires the HTTP call.
        """
        raise NotImplementedError(
            "StepCAClient.health_check lands in Phase 2 of the mTLS rollout"
        )
