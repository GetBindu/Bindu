"""Tunnel configuration models."""

from dataclasses import dataclass, field
from typing import Optional


def _get_default_server_address() -> str:
    """Get default server address from settings."""
    from bindu.settings import app_settings

    return app_settings.tunnel.default_server_address


def _get_default_tunnel_domain() -> str:
    """Get default tunnel domain from settings."""
    from bindu.settings import app_settings

    return app_settings.tunnel.default_tunnel_domain


@dataclass
class TunnelConfig:
    """Configuration for FRP tunnel setup.

    Attributes:
        enabled: Whether tunneling is enabled
        server_address: FRP server control endpoint (host:port)
        subdomain: Custom subdomain for the tunnel (auto-generated if None)
        tunnel_domain: Base domain for tunnels
        protocol: Protocol type (http, https, tcp)
        use_tls: Whether to use TLS for FRP connection
        local_host: Local host to tunnel (default: 127.0.0.1)
        local_port: Local port to tunnel (set at runtime)
    """

    enabled: bool = False
    server_address: str = field(default_factory=_get_default_server_address)
    subdomain: Optional[str] = None
    tunnel_domain: str = field(default_factory=_get_default_tunnel_domain)
    protocol: str = "http"
    use_tls: bool = False
    local_host: str = "127.0.0.1"
    local_port: Optional[int] = None

    def get_public_url(self) -> str:
        """Get the public URL for this tunnel.

        Returns:
            Public URL string (e.g., https://myapp.tunnel.getbindu.com)
        """
        if not self.subdomain:
            raise ValueError("Subdomain must be set to generate public URL")

        # Always use https for public tunnel URLs (FRP server handles TLS termination)
        return f"https://{self.subdomain}.{self.tunnel_domain}"
