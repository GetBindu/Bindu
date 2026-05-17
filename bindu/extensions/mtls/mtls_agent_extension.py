# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""mTLS extension orchestrator for Bindu agents.

This class is the integration seam between the agent bootstrap (``bindufy``),
the on-disk cert store, and the step-ca client. It mirrors the role
``DIDAgentExtension`` plays for identity — both are constructed once at
startup and reused for the lifetime of the agent.

Phase 1 scope (this commit)
---------------------------
- Class signature, settings/state wiring, property surface.
- Method skeletons documenting the public API.

Phase 2 will land the bootstrap flow (cert fetch + Vault backup), Phase 3 the
server TLS wrapping (``ssl.SSLContext`` + gRPC server credentials), Phase 4
the client TLS wrapping, and Phase 6 the in-process renewal task.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from bindu.extensions.mtls.cert_store import CertStore
from bindu.extensions.mtls.step_ca_client import StepCAClient
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.mtls.extension")


class MTLSAgentExtension:
    """Lifecycle manager for an agent's X.509 certificate.

    Owns three concerns:

    1. **Bootstrap.** ``initialize()`` at agent startup — load from disk, or
       fetch a fresh cert from step-ca using the agent's Hydra OIDC token.
    2. **Server material.** Properties that hand the live HTTP and gRPC
       servers everything they need to start in mTLS mode.
    3. **Client material.** Properties that hand outbound HTTP/gRPC clients
       the cert/key/CA-bundle they need to authenticate as this agent.

    Renewal is driven externally by a periodic task that calls
    ``renew_if_needed()``.
    """

    def __init__(
        self,
        pki_dir: Path,
        agent_did: str,
        agent_url: Optional[str] = None,
        oidc_token_provider=None,
    ):
        """Wire dependencies.

        Args:
            pki_dir: Directory where cert material is persisted. The DID
                extension creates this; we co-locate to keep a single backup
                surface.
            agent_did: The agent's DID. Used as CN and URI SAN in the CSR.
            agent_url: Optional agent base URL. When provided, its hostname is
                added as a DNS SAN so off-the-shelf TLS clients can verify by
                hostname.
            oidc_token_provider: Async callable returning a fresh Hydra OIDC
                token. Injected so the extension does not import Hydra glue
                directly, keeping the dependency graph one-way.
        """
        self.pki_dir = Path(pki_dir)
        self.agent_did = agent_did
        self.agent_url = agent_url
        self._oidc_token_provider = oidc_token_provider
        self._store = CertStore(self.pki_dir)
        self._ca = StepCAClient()
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle (bodies land in Phase 2 and Phase 6)
    # ------------------------------------------------------------------

    async def initialize(self) -> bool:
        """Bootstrap the agent's mTLS material.

        Steps:
            1. Ensure the CA bundle is on disk (fetch from step-ca if missing).
            2. If a valid cert exists and is not near expiry, use it.
            3. Otherwise generate a fresh keypair + CSR and sign via step-ca.
            4. Optionally back up to Vault.

        Returns:
            True on success. Logs and returns False on a recoverable failure;
            raises only on misconfiguration the operator must fix.
        """
        raise NotImplementedError(
            "MTLSAgentExtension.initialize lands in Phase 2 of the mTLS rollout"
        )

    async def renew_if_needed(self) -> bool:
        """Re-issue the cert when fewer than ``renew_before_hours`` remain.

        Returns:
            True when a renewal happened; False when the existing cert is
            still good or when step-ca is unreachable and the cycle is
            skipped.
        """
        raise NotImplementedError(
            "MTLSAgentExtension.renew_if_needed lands in Phase 6 of the mTLS rollout"
        )

    # ------------------------------------------------------------------
    # Server material (Phase 3)
    # ------------------------------------------------------------------

    def build_server_ssl_context(self):
        """Return an ``ssl.SSLContext`` for uvicorn.

        Configured with the agent cert/key, the CA bundle as the trust root
        for peer verification, and ``CERT_REQUIRED`` when
        ``mtls.require_client_cert`` is true.
        """
        raise NotImplementedError(
            "MTLSAgentExtension.build_server_ssl_context lands in Phase 3"
        )

    def build_grpc_server_credentials(self):
        """Return ``grpc.ServerCredentials`` for the gRPC bind.

        Equivalent of ``ssl_server_credentials(..., require_client_auth=True)``
        built from the same on-disk PEM files as the HTTP context.
        """
        raise NotImplementedError(
            "MTLSAgentExtension.build_grpc_server_credentials lands in Phase 3"
        )

    # ------------------------------------------------------------------
    # Client material (Phase 4)
    # ------------------------------------------------------------------

    def get_httpx_client_kwargs(self) -> dict:
        """Return kwargs to splat into ``httpx.AsyncClient(...)``.

        Includes ``cert=(cert_path, key_path)`` and ``verify=ca_bundle_path``
        so outbound calls authenticate as this agent and validate peers
        against the cluster CA.
        """
        raise NotImplementedError(
            "MTLSAgentExtension.get_httpx_client_kwargs lands in Phase 4"
        )

    def build_grpc_channel_credentials(self):
        """Return ``grpc.ChannelCredentials`` for outbound gRPC."""
        raise NotImplementedError(
            "MTLSAgentExtension.build_grpc_channel_credentials lands in Phase 4"
        )

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def store(self) -> CertStore:
        """Underlying ``CertStore``. Exposed for tests and diagnostic tooling."""
        return self._store

    @property
    def cert_fingerprint(self) -> Optional[str]:
        """SHA-256 fingerprint of the active cert, or None when no cert is on disk."""
        return self._store.get_cert_fingerprint()

    @property
    def enabled(self) -> bool:
        """Convenience accessor for the global toggle."""
        return app_settings.mtls.enabled
