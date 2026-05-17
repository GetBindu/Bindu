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

Phase coverage
--------------
* Phase 2 (this commit): ``initialize()`` bootstraps the agent's cert from
  step-ca and persists it. Server / client material builders and the
  background renewal task remain stubs.
* Phase 3 will return live ``ssl.SSLContext`` and ``grpc.ServerCredentials``.
* Phase 4 will hand outbound clients their cert/key.
* Phase 6 will land the renewal loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable, Optional

from bindu.extensions.mtls.cert_store import CertStore
from bindu.extensions.mtls.step_ca_client import StepCAClient, StepCAError
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.mtls.extension")


# A token provider is any async callable returning a Hydra OIDC access token.
# Injecting it keeps the extension free of direct Hydra imports — the wiring
# lives in ``bindu.penguin.mtls_setup``.
OIDCTokenProvider = Callable[[], Awaitable[str]]


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
        oidc_token_provider: Optional[OIDCTokenProvider] = None,
        step_ca: Optional[StepCAClient] = None,
        cert_store: Optional[CertStore] = None,
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
            step_ca: Optional pre-built step-ca client. Tests pass a fake;
                production code lets the constructor build one from settings.
            cert_store: Optional pre-built cert store. Same rationale as
                ``step_ca``.
        """
        self.pki_dir = Path(pki_dir)
        self.agent_did = agent_did
        self.agent_url = agent_url
        self._oidc_token_provider = oidc_token_provider
        self._store = cert_store if cert_store is not None else CertStore(self.pki_dir)
        self._ca = step_ca if step_ca is not None else StepCAClient()
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self, force_renew: bool = False) -> bool:
        """Bootstrap the agent's mTLS material.

        Steps:
            1. Ensure the CA bundle is on disk (fetch from step-ca if missing).
            2. If a valid cert exists and is not near expiry — and ``force_renew``
               is False — reuse it.
            3. Otherwise generate a fresh keypair + CSR and have step-ca sign it.

        Args:
            force_renew: When True, skip the reuse-existing-cert path and
                always go to step-ca. The renewal loop sets this to True.

        Returns:
            True on success. Logs and returns False on recoverable failure
            (e.g. step-ca temporarily unreachable); raises only on
            misconfiguration the operator must fix.
        """
        if self._oidc_token_provider is None:
            raise RuntimeError(
                "MTLSAgentExtension.initialize() requires an oidc_token_provider; "
                "the agent must complete Hydra registration first."
            )

        try:
            await self._ensure_ca_bundle()
            renewal_due = self._store.is_renewal_due(
                app_settings.mtls.renew_before_hours
            )
            if not force_renew and self._store.has_cert() and not renewal_due:
                logger.info(
                    "mTLS cert already on disk and valid (fingerprint=%s)",
                    self._store.get_cert_fingerprint(),
                )
                self._initialized = True
                return True

            await self._issue_new_cert()
            self._initialized = True
            logger.info(
                "mTLS bootstrap complete for %s (fingerprint=%s)",
                self.agent_did,
                self._store.get_cert_fingerprint(),
            )
            return True
        except StepCAError as exc:
            logger.error("mTLS bootstrap failed against step-ca: %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected mTLS bootstrap error: %s", exc)
            return False

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

    async def close(self) -> None:
        """Release the underlying step-ca HTTP sessions."""
        await self._ca.close()

    # ------------------------------------------------------------------
    # Internal — bootstrap steps
    # ------------------------------------------------------------------

    async def _ensure_ca_bundle(self) -> None:
        """Fetch the CA bundle from step-ca when it isn't already on disk."""
        if self._store.has_ca_bundle():
            return
        logger.info("Fetching CA bundle from step-ca…")
        bundle = await self._ca.fetch_root_ca()
        self._store.write_ca_bundle(bundle)

    async def _issue_new_cert(self) -> None:
        """Generate a keypair, build a CSR, and have step-ca sign it.

        Always rotates the private key. Reusing a key across renewals would
        defeat the point of having a short-TTL cert.
        """
        assert self._oidc_token_provider is not None  # type guard

        private_key, _ = self._store.generate_keypair()
        csr_pem = self._store.build_csr(
            private_key, self.agent_did, agent_url=self.agent_url
        )

        token = await self._oidc_token_provider()
        if not token:
            raise StepCAError(
                "OIDC token provider returned an empty token; Hydra likely rejected the credentials"
            )

        cert_pem, chain_pem = await self._ca.sign_csr(csr_pem, token)
        self._store.write_cert(cert_pem)
        # Refresh the CA bundle from the sign response — step-ca returns the
        # currently-active chain, which may have rotated since the agent last
        # fetched ``/roots.pem``.
        self._store.write_ca_bundle(chain_pem)

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

    @property
    def initialized(self) -> bool:
        """True once ``initialize()`` has completed successfully."""
        return self._initialized
