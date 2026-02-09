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
        """Initialize tunnel manager."""
        self.active_tunnel: Optional[Tunnel] = None

    def create_tunnel(
        self,
        local_port: int,
        config: Optional[TunnelConfig] = None,
        subdomain: Optional[str] = None,
    ) -> str:
        """Create a tunnel to expose a local port.

        Args:
            local_port: Local port to tunnel
            config: Tunnel configuration (uses defaults if None)
            subdomain: Custom subdomain (auto-generated if None)

        Returns:
            Public URL for the tunnel

        Raises:
            RuntimeError: If tunnel is already active
            ValueError: If tunnel creation fails
        """
        if self.active_tunnel is not None:
            raise RuntimeError(
                "A tunnel is already active. Stop it before creating a new one."
            )

        # Create config if not provided
        if config is None:
            config = TunnelConfig(enabled=True)

        # Set local port
        config.local_port = local_port

        # Generate subdomain if not provided
        if subdomain:
            config.subdomain = subdomain
        elif not config.subdomain:
            config.subdomain = self._generate_subdomain()

        logger.info(
            f"Creating tunnel for localhost:{local_port} with subdomain '{config.subdomain}'"
        )

        # Create and start tunnel
        tunnel = Tunnel(config)
        try:
            public_url = tunnel.start()
            self.active_tunnel = tunnel
            return public_url
        except Exception as e:
            logger.error(f"Failed to create tunnel: {e}")
            raise

    def stop_tunnel(self) -> None:
        """Stop the active tunnel if any."""
        if self.active_tunnel:
            self.active_tunnel.stop()
            self.active_tunnel = None
            logger.info("Tunnel stopped")
        else:
            logger.debug("No active tunnel to stop")

    def get_public_url(self) -> Optional[str]:
        """Get the public URL of the active tunnel.

        Returns:
            Public URL or None if no tunnel is active
        """
        if self.active_tunnel:
            return self.active_tunnel.public_url
        return None

    @staticmethod
    def _generate_subdomain_from_did(agent_did: str) -> str:
        """Generate a subdomain from agent DID.

        Converts DID to a DNS-safe subdomain by:
        - Removing 'did:' prefix
        - Replacing colons with hyphens
        - Converting to lowercase
        - Truncating if too long (max 63 chars for DNS)

        Args:
            agent_did: Agent DID (e.g., did:bindu:user:agent:id)

        Returns:
            DNS-safe subdomain string
        """
        # Remove 'did:' prefix and replace colons with hyphens
        subdomain = agent_did.replace("did:", "").replace(":", "-").lower()

        # Replace underscores and other special chars with hyphens
        subdomain = subdomain.replace("_", "-").replace("@", "-at-").replace(".", "-")

        # Remove any characters that aren't alphanumeric or hyphens
        subdomain = "".join(c if c.isalnum() or c == "-" else "" for c in subdomain)

        # Ensure it starts with a letter (DNS requirement)
        if subdomain and not subdomain[0].isalpha():
            subdomain = "a" + subdomain

        # Truncate to 63 characters (DNS label limit)
        if len(subdomain) > 63:
            subdomain = subdomain[:63]

        # Remove trailing hyphens
        subdomain = subdomain.rstrip("-")

        return subdomain or "agent"  # Fallback if empty

    @staticmethod
    def _generate_subdomain(length: int = 12) -> str:
        """Generate a random subdomain.

        Args:
            length: Length of the subdomain

        Returns:
            Random subdomain string
        """
        # Use lowercase letters and numbers
        alphabet = string.ascii_lowercase + string.digits
        # Start with a letter (some DNS systems require this)
        subdomain = secrets.choice(string.ascii_lowercase)
        subdomain += "".join(secrets.choice(alphabet) for _ in range(length - 1))
        return subdomain

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup tunnel."""
        self.stop_tunnel()
        return False
