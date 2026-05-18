# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""mTLS authentication middleware.

Extracts the peer (client) X.509 certificate from the ASGI TLS extension,
parses out the agent DID (URI SAN preferred, CN fallback), and injects it
into the request scope so downstream handlers can authorize off the
cryptographic identity rather than a token.

Composes with HydraMiddleware under ``mtls.mode``:

* ``"hybrid"`` — this middleware extracts the peer DID; Hydra still
  introspects the bearer token. Requests must satisfy *both* layers, and
  the cert CN must match the Hydra ``client_id``. This is the rollout
  default while every agent is migrated to a cert.
* ``"mtls"``  — this middleware is the sole authentication layer; Hydra
  introspection is skipped. The target end state.
* ``"off"``   — middleware short-circuits, behavior is identical to a
  deployment without mTLS wired in.

Peer cert plumbing follows the ASGI TLS extension spec
(https://asgi.readthedocs.io/en/latest/extensions.html#tls): uvicorn
exposes ``scope["extensions"]["tls"]["client_cert_chain"]`` as a list of
PEM-encoded certs when ``ssl_cert_reqs=ssl.CERT_REQUIRED`` is set.
"""

from __future__ import annotations

import fnmatch
import re
from typing import Any, Callable, Optional

from cryptography import x509
from cryptography.x509.oid import NameOID

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.mtls")


SCOPE_KEY_PEER_DID = "bindu_peer_did"
SCOPE_KEY_PEER_CERT = "bindu_peer_cert"


class MTLSMiddleware:
    """ASGI middleware that turns a verified peer cert into a DID.

    Placement: install **before** ``HydraMiddleware`` in hybrid mode so the
    peer DID is available when Hydra cross-checks the token's ``client_id``;
    install in place of ``HydraMiddleware`` in mtls-only mode.
    """

    def __init__(self, app: Callable, mtls_config: Any) -> None:
        """Wire the middleware.

        Args:
            app: The next ASGI application in the chain.
            mtls_config: Typically ``app_settings.mtls``. Read for ``mode``,
                ``require_client_cert``, and the public-endpoint allowlist
                (reuses Hydra's list — both middlewares should agree on what
                bypasses auth).
        """
        self.app = app
        self.config = mtls_config

        # Reuse Hydra's public-endpoint list so /health, /.well-known/...,
        # etc. don't require a peer cert. Operators who tune the allowlist
        # only have to maintain one knob.
        self._public_patterns: list[re.Pattern[str]] = []
        for pattern in getattr(app_settings.hydra, "public_endpoints", []):
            self._public_patterns.append(re.compile(fnmatch.translate(pattern)))

    async def __call__(self, scope, receive, send):
        """ASGI entry point."""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        if self.config.mode == "off" or not self.config.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if self._is_public_endpoint(path):
            await self.app(scope, receive, send)
            return

        cert_chain = self._extract_cert_chain(scope)
        if not cert_chain:
            if self.config.require_client_cert:
                await self._reject(send, 403, "Client certificate required")
                return
            # Soft mode — no peer cert but mTLS doesn't strictly require one.
            await self.app(scope, receive, send)
            return

        leaf_pem = cert_chain[0]
        peer_did = self._extract_did(leaf_pem)
        if peer_did is None:
            await self._reject(
                send, 403, "Client certificate lacks an identifiable DID"
            )
            return

        scope[SCOPE_KEY_PEER_DID] = peer_did
        scope[SCOPE_KEY_PEER_CERT] = leaf_pem
        logger.debug("mTLS peer authenticated: %s", peer_did)
        await self.app(scope, receive, send)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_public_endpoint(self, path: str) -> bool:
        return any(p.match(path) for p in self._public_patterns)

    @staticmethod
    def _extract_cert_chain(scope) -> list[str]:
        """Pull the peer cert chain from the ASGI TLS extension.

        Returns an empty list when TLS isn't wired (e.g. local dev over
        plain HTTP), the handshake didn't surface a cert, or the server
        doesn't implement the ASGI TLS extension. Callers decide whether
        absence is fatal.
        """
        extensions = scope.get("extensions") or {}
        tls = extensions.get("tls") or {}
        chain = tls.get("client_cert_chain") or []
        # ASGI spec types this as list[str] (PEM). Defensive: filter to strs.
        return [c for c in chain if isinstance(c, str)]

    @staticmethod
    def _extract_did(cert_pem: str) -> Optional[str]:
        """Pull the DID out of a PEM cert.

        Prefers a URI SAN whose value starts with ``did:`` (the cleaner
        identity carrier); falls back to the CN when no SAN matches.
        Returns None when neither yields a DID.
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            logger.warning("Could not parse peer cert PEM: %s", exc)
            return None

        # Preferred path — URI SAN.
        try:
            san = cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value
            for uri in san.get_values_for_type(x509.UniformResourceIdentifier):
                if uri.startswith("did:"):
                    return uri
        except x509.ExtensionNotFound:
            pass

        # Fallback — CN. Legacy peers may not carry a SAN. The cryptography
        # API types ``NameAttribute.value`` as ``str | bytes``; we only
        # accept str-shaped DIDs.
        try:
            cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if cn_attrs:
                cn_value = cn_attrs[0].value
                if isinstance(cn_value, str) and cn_value.startswith("did:"):
                    return cn_value
        except IndexError:
            pass

        return None

    @staticmethod
    async def _reject(send, status: int, message: str) -> None:
        """Emit a minimal ASGI 4xx response.

        Kept dependency-free (no Starlette JSONResponse) so the middleware
        can run before any application-level error handlers.
        """
        body = (
            b'{"error":{"code":'
            + str(status).encode("ascii")
            + b',"message":"'
            + message.encode("utf-8")
            + b'"}}'
        )
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})
