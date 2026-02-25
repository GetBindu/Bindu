"""Tunnel manager for creating and managing tunnels."""

import secrets
import string
from typing import Optional

from bindu.tunneling.config import TunnelConfig
from bindu.tunneling.tunnel import Tunnel
from bindu.utils.logging import get_logger

logger = get_logger("bindu.tunneling.manager")


class TunnelManager:
    """Manages tunnel creation and lifecycle."""

    def __init__(self):
        self.active_tunnel: Optional[Tunnel] = None

    def create_tunnel(
        self,
        local_port: int,
        config: Optional[TunnelConfig] = None,
        subdomain: Optional[str] = None,
    ) -> str:
        """Create a tunnel to expose a local port."""

        if not isinstance(local_port, int) or not (1 <= local_port <= 65535):
            raise ValueError("local_port must be an integer between 1 and 65535")

        if self.active_tunnel is not None:
            raise RuntimeError(
                "A tunnel is already active. Stop it before creating a new one."
            )

        if config is None:
            config = TunnelConfig(enabled=True)

        config.local_port = local_port

        if subdomain:
            config.subdomain = subdomain
        elif not config.subdomain:
            config.subdomain = self._generate_subdomain()

        logger.info(
            f"Creating tunnel for localhost:{local_port} with subdomain '{config.subdomain}'"
        )

        tunnel = Tunnel(config)

        try:
            public_url = tunnel.start()
            self.active_tunnel = tunnel
            logger.info(f"Tunnel started successfully at {public_url}")
            return public_url
        except Exception:
            logger.exception("Failed to create tunnel during startup")
            raise

    def stop_tunnel(self) -> None:
        if self.active_tunnel:
            try:
                self.active_tunnel.stop()
                logger.info("Tunnel stopped")
            except Exception:
                logger.exception("Error while stopping tunnel")
            finally:
                self.active_tunnel = None
        else:
            logger.debug("No active tunnel to stop")

    def get_public_url(self) -> Optional[str]:
        if self.active_tunnel:
            return self.active_tunnel.public_url
        return None

    @staticmethod
    def _generate_subdomain_from_did(agent_did: str) -> str:
        subdomain = agent_did.replace("did:", "").replace(":", "-").lower()
        subdomain = subdomain.replace("_", "-").replace("@", "-at-").replace(".", "-")
        subdomain = "".join(c if c.isalnum() or c == "-" else "" for c in subdomain)

        if subdomain and not subdomain[0].isalpha():
            subdomain = "a" + subdomain

        if len(subdomain) > 63:
            subdomain = subdomain[:63]

        subdomain = subdomain.rstrip("-")
        return subdomain or "agent"

    @staticmethod
    def _generate_subdomain(length: int = 12) -> str:
        alphabet = string.ascii_lowercase + string.digits
        subdomain = secrets.choice(string.ascii_lowercase)
        subdomain += "".join(secrets.choice(alphabet) for _ in range(length - 1))
        return subdomain

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_tunnel()
        return False