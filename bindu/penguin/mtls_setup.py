"""mTLS setup utilities for the penguin module.

Mirrors ``did_setup.py``: a thin synchronous facade over the async
``MTLSAgentExtension`` so ``bindufy`` (which runs synchronously) can wire mTLS
without touching the event loop directly.

The bootstrap order is:

1. DID extension is initialized (``did_setup``).
2. Agent registers as an OAuth2 client in Hydra (``_register_in_hydra``).
3. **This module runs** — using the Hydra credentials to fetch an OIDC token,
   which is exchanged at step-ca for an X.509 cert.
4. Manifest is created, server is started, etc.

The function returns ``None`` when ``mtls.enabled`` is false, when Hydra
credentials are unavailable (mTLS without Hydra OIDC isn't supported in this
rollout), or when bootstrap fails — callers must handle ``None`` by either
running in plain-HTTP mode or aborting, per ``mtls.require_client_cert``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from bindu.common.models import AgentCredentials
from bindu.extensions.mtls import MTLSAgentExtension
from bindu.settings import app_settings
from bindu.utils.http.tokens import get_client_credentials_token
from bindu.utils.logging import get_logger

logger = get_logger("bindu.penguin.mtls_setup")


def _build_token_provider(credentials: AgentCredentials):
    """Build the async OIDC token provider closed over Hydra credentials.

    step-ca's OIDC provisioner expects an OIDC ID token signed by Hydra.
    Hydra returns ``id_token`` when ``openid`` is included in the scope on a
    client_credentials grant (provisioner config dependent); we fall back to
    ``access_token`` so misconfigured deployments fail loudly at step-ca
    rather than silently here.
    """

    async def _provider() -> str:
        result = await get_client_credentials_token(
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            scope="openid",
            # step-ca's OIDC provisioner enforces this — without an ``aud``
            # claim matching its configured client ID the sign request 403s.
            audience=app_settings.mtls.oidc_audience,
        )
        if not result:
            logger.error("Hydra returned no token for client %s", credentials.client_id)
            return ""
        return result.get("id_token") or result.get("access_token", "")

    return _provider


async def _bootstrap_async(
    pki_dir: Path,
    agent_did: str,
    agent_url: Optional[str],
    credentials: AgentCredentials,
    agent_id_str: str,
) -> Optional[MTLSAgentExtension]:
    """Async core: construct the extension, initialize, optionally back up.

    Kept private so the sync caller in ``bindufy`` only sees the wrapper.
    """
    extension = MTLSAgentExtension(
        pki_dir=pki_dir,
        agent_did=agent_did,
        agent_url=agent_url,
        oidc_token_provider=_build_token_provider(credentials),
    )

    try:
        ok = await extension.initialize()
    finally:
        await extension.close()

    if not ok:
        return None

    if app_settings.vault.enabled:
        await _backup_mtls_to_vault(agent_id_str, extension)

    return extension


async def _backup_mtls_to_vault(
    agent_id_str: str, extension: MTLSAgentExtension
) -> None:
    """Back up the freshly-issued cert material to Vault.

    Failures are logged but do not abort the agent — Vault is a durability
    aid (restart-recovery), not a hard dependency of the bootstrap.
    """
    from bindu.utils.http.vault_client import VaultClient

    store = extension.store
    vault = VaultClient()
    try:
        await vault.store_mtls_material(
            agent_id=agent_id_str,
            cert_pem=store.read_cert().decode("ascii"),
            key_pem=store.read_key().decode("ascii"),
            ca_bundle_pem=store.read_ca_bundle().decode("ascii"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to back up mTLS material to Vault: %s", exc)
    finally:
        await vault.close()


def initialize_mtls_extension(
    agent_id: str,
    agent_did: str,
    agent_url: Optional[str],
    pki_dir: Path,
    hydra_credentials: Optional[AgentCredentials],
) -> Optional[MTLSAgentExtension]:
    """Bootstrap the mTLS extension for an agent.

    Returns ``None`` (and logs) when:
      * ``app_settings.mtls.enabled`` is False — the feature is opt-in.
      * ``hydra_credentials`` is None — step-ca requires a Hydra OIDC token
        for the OIDC provisioner; without Hydra registration we cannot
        bootstrap a cert.
      * ``MTLSAgentExtension.initialize()`` returns False — typically step-ca
        unreachable or the OIDC token was rejected. Caller decides whether
        this is fatal (``require_client_cert=True``) or recoverable.

    Returns the initialized extension on success.
    """
    if not app_settings.mtls.enabled:
        logger.debug("mTLS disabled (mtls.enabled=False); skipping bootstrap")
        return None

    if hydra_credentials is None:
        logger.error(
            "mTLS bootstrap requires Hydra credentials, but none were supplied. "
            "Enable Hydra auth (auth.enabled=True, auth.provider=hydra) or disable mTLS."
        )
        return None

    logger.info("Bootstrapping mTLS cert for %s via step-ca…", agent_did)
    try:
        return asyncio.run(
            _bootstrap_async(
                pki_dir=pki_dir,
                agent_did=agent_did,
                agent_url=agent_url,
                credentials=hydra_credentials,
                agent_id_str=agent_id,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("mTLS bootstrap raised: %s", exc)
        return None
