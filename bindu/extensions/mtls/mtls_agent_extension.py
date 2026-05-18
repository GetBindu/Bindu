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

import asyncio
import ssl
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import grpc

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
        if not self._store.is_renewal_due(app_settings.mtls.renew_before_hours):
            return False
        # step-ca down? Don't burn cycles thrashing — wait for the next tick.
        # The cert has hours of headroom by design, so a few missed cycles
        # are fine.
        if not await self._ca.health_check():
            logger.warning("step-ca unhealthy; deferring renewal")
            return False
        logger.info(
            "mTLS cert near expiry (renew_before_hours=%d); renewing",
            app_settings.mtls.renew_before_hours,
        )
        return await self.initialize(force_renew=True)

    async def run_renewal_loop(self, interval_seconds: int | None = None) -> None:
        """Run the renewal check forever; intended for ``asyncio.create_task``.

        Sleeps for ``interval_seconds`` between checks (defaults to
        ``MTLSSettings.renew_check_interval_seconds``). Exits cleanly on
        cancellation; logs and continues on any other exception.

        Args:
            interval_seconds: Override for the renew check cadence. The
                renewal margin (``renew_before_hours``) gives the loop ample
                room to miss a check or two without the cert lapsing.
        """
        interval = (
            interval_seconds
            if interval_seconds is not None
            else app_settings.mtls.renew_check_interval_seconds
        )
        logger.info("mTLS renewal loop started (interval=%ds)", interval)
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    await self.renew_if_needed()
                except Exception as exc:  # noqa: BLE001
                    # Renewal loop must never die from a transient error;
                    # logging + continuing is the right shape.
                    logger.exception("mTLS renewal cycle failed: %s", exc)
        except asyncio.CancelledError:
            logger.info("mTLS renewal loop cancelled")
            raise

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
        # Write the leaf + intermediate concatenated so the TLS handshake
        # presents the full chain to peers. step-ca's response is shaped:
        #   crt = leaf
        #   ca  = the intermediate that signed the leaf
        # The trust anchor (root) is fetched separately via
        # ``_ensure_ca_bundle`` and lives in ``ca_bundle.pem``; we
        # deliberately do NOT overwrite it here. Doing so would replace
        # the root with the intermediate, leaving peers unable to verify
        # any chain back to the trust anchor.
        self._store.write_cert(cert_pem + chain_pem)

    # ------------------------------------------------------------------
    # Server material
    # ------------------------------------------------------------------

    def build_server_ssl_context(self) -> ssl.SSLContext:
        """Return an ``ssl.SSLContext`` configured for mTLS.

        The context loads the agent cert/key as the server identity and the
        CA bundle as the trust root for verifying peer (client) certs. Verify
        mode is ``CERT_REQUIRED`` when ``mtls.require_client_cert`` is true
        (full mTLS) or ``CERT_OPTIONAL`` otherwise.

        Raises:
            FileNotFoundError: when cert / key / CA-bundle are not on disk.
                ``initialize()`` must run first.
        """
        self._require_initialized()
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            certfile=str(self._store.cert_path),
            keyfile=str(self._store.key_path),
        )
        context.load_verify_locations(cafile=str(self._store.ca_bundle_path))
        context.verify_mode = (
            ssl.CERT_REQUIRED
            if app_settings.mtls.require_client_cert
            else ssl.CERT_OPTIONAL
        )
        return context

    def get_uvicorn_ssl_kwargs(self) -> dict[str, Any]:
        """Return the ``ssl_*`` kwargs to splat into ``uvicorn.run(...)``.

        Uvicorn accepts file paths and an ssl_cert_reqs flag rather than a
        constructed ``SSLContext``, so this method hands back the file-path
        form. Use ``build_server_ssl_context`` when a Python ``SSLContext`` is
        needed directly (tests, diagnostics).
        """
        self._require_initialized()
        return {
            "ssl_certfile": str(self._store.cert_path),
            "ssl_keyfile": str(self._store.key_path),
            "ssl_ca_certs": str(self._store.ca_bundle_path),
            "ssl_cert_reqs": (
                ssl.CERT_REQUIRED
                if app_settings.mtls.require_client_cert
                else ssl.CERT_OPTIONAL
            ),
        }

    def build_grpc_server_credentials(self) -> grpc.ServerCredentials:
        """Return ``grpc.ServerCredentials`` for the gRPC bind.

        Built from the same on-disk PEM files as the HTTP context, so an
        attacker can't downgrade by hitting the gRPC port instead.
        """
        self._require_initialized()
        cert = self._store.read_cert()
        key = self._store.read_key()
        ca_bundle = self._store.read_ca_bundle()
        return grpc.ssl_server_credentials(
            [(key, cert)],
            root_certificates=ca_bundle,
            require_client_auth=app_settings.mtls.require_client_cert,
        )

    def _require_initialized(self) -> None:
        """Guard rail — server material is only valid post-bootstrap."""
        if not self._store.has_cert():
            raise FileNotFoundError(
                f"No mTLS cert at {self._store.cert_path}; "
                "call MTLSAgentExtension.initialize() before building server material"
            )

    # ------------------------------------------------------------------
    # Client material
    # ------------------------------------------------------------------

    def build_client_ssl_context(self) -> ssl.SSLContext:
        """Return an ``ssl.SSLContext`` for outbound (client-side) connections.

        The context carries this agent's cert/key as the client identity and
        trusts the CA bundle for verifying peer (server) certs. Suitable for
        passing as ``ssl=...`` to ``aiohttp.TCPConnector`` or as ``verify=...``
        / ``cert=...`` to httpx.
        """
        self._require_initialized()
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_cert_chain(
            certfile=str(self._store.cert_path),
            keyfile=str(self._store.key_path),
        )
        context.load_verify_locations(cafile=str(self._store.ca_bundle_path))
        context.check_hostname = app_settings.mtls.verify_server_cert
        context.verify_mode = (
            ssl.CERT_REQUIRED if app_settings.mtls.verify_server_cert else ssl.CERT_NONE
        )
        return context

    def get_httpx_client_kwargs(self) -> dict[str, Any]:
        """Return kwargs to splat into ``httpx.AsyncClient(...)``.

        Hands httpx the cert+key tuple and the CA-bundle path. The project's
        primary HTTP client is aiohttp-backed (``AsyncHTTPClient``), but this
        is provided for any callers that integrate with httpx directly.
        """
        self._require_initialized()
        return {
            "cert": (str(self._store.cert_path), str(self._store.key_path)),
            "verify": str(self._store.ca_bundle_path),
        }

    def build_grpc_channel_credentials(self) -> grpc.ChannelCredentials:
        """Return ``grpc.ChannelCredentials`` for outbound gRPC.

        Built from the same on-disk PEM files as the server credentials so a
        downgrade is impossible.
        """
        self._require_initialized()
        cert = self._store.read_cert()
        key = self._store.read_key()
        ca_bundle = self._store.read_ca_bundle()
        return grpc.ssl_channel_credentials(
            root_certificates=ca_bundle,
            private_key=key,
            certificate_chain=cert,
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
