"""Configuration for Ory Hydra and Kratos integration."""

from __future__ import annotations as _annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class HydraConfig(BaseModel):
    """Hydra configuration."""

    enabled: bool = Field(default=True, description="Enable Hydra authentication")
    admin_url: HttpUrl = Field(
        default="http://localhost:4445", description="Hydra Admin API URL"
    )
    public_url: HttpUrl = Field(
        default="http://localhost:4444", description="Hydra Public API URL"
    )
    timeout: int = Field(default=10, description="Request timeout in seconds")
    verify_ssl: bool = Field(
        default=False, description="Verify SSL certificates (disable for self-signed)"
    )

    # Token cache settings
    cache_ttl: int = Field(default=300, description="Token cache TTL in seconds")
    max_cache_size: int = Field(default=1000, description="Maximum cache entries")

    # OAuth2 settings
    token_lifetimes: Dict[str, int] = Field(
        default={
            "access_token": 3600,  # 1 hour
            "refresh_token": 2592000,  # 30 days
            "id_token": 3600,  # 1 hour
        },
        description="Token lifetimes in seconds",
    )

    # Client configuration
    default_client: Dict[str, Any] = Field(
        default={
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "openid offline profile email",
            "token_endpoint_auth_method": "client_secret_basic",
            "redirect_uris": ["http://localhost:3000/oauth/callback"],
        },
        description="Default OAuth2 client configuration",
    )


class KratosConfig(BaseModel):
    """Kratos configuration."""

    enabled: bool = Field(default=True, description="Enable Kratos identity management")
    admin_url: HttpUrl = Field(
        default="http://localhost:4434", description="Kratos Admin API URL"
    )
    public_url: HttpUrl = Field(
        default="http://localhost:4433", description="Kratos Public API URL"
    )
    timeout: int = Field(default=10, description="Request timeout in seconds")
    verify_ssl: bool = Field(default=False, description="Verify SSL certificates")

    # Encryption settings
    encryption_key: Optional[str] = Field(
        default=None,
        description="Fernet key for encrypting OAuth tokens (32-byte URL-safe base64)",
    )

    # Identity schema
    default_schema_id: str = Field(
        default="default", description="Default identity schema ID"
    )

    # Session settings
    session_lifespan: int = Field(
        default=2592000, description="Session lifespan in seconds (30 days)"
    )

    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        """Validate encryption key format."""
        if v is None:
            return v

        import base64

        try:
            # Check if it's a valid Fernet key (32-byte URL-safe base64)
            decoded = base64.urlsafe_b64decode(v)
            if len(decoded) != 32:
                raise ValueError("Encryption key must be 32 bytes when decoded")
            return v
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}")


class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration."""

    name: str = Field(..., description="Provider name (notion, google, github, etc.)")
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    auth_url: HttpUrl = Field(..., description="Authorization URL")
    token_url: HttpUrl = Field(..., description="Token URL")
    userinfo_url: Optional[HttpUrl] = Field(None, description="User info URL")
    scope: str = Field(..., description="Default scope")
    redirect_uri: HttpUrl = Field(..., description="Redirect URI")


class OryConfig(BaseModel):
    """Main Ory configuration."""

    hydra: HydraConfig = Field(default_factory=HydraConfig)
    kratos: KratosConfig = Field(default_factory=KratosConfig)

    # OAuth providers
    oauth_providers: Dict[str, OAuthProviderConfig] = Field(
        default_factory=dict, description="Configured OAuth providers"
    )

    # Feature flags
    enable_m2m_auth: bool = Field(
        default=True, description="Enable machine-to-machine authentication"
    )
    enable_user_auth: bool = Field(
        default=True, description="Enable user authentication"
    )
    enable_credential_storage: bool = Field(
        default=True, description="Enable OAuth credential storage"
    )

    # Public endpoints that don't require authentication
    public_endpoints: List[str] = Field(
        default=[
            "/",
            "/health",
            "/healthz",
            "/ready",
            "/openapi.json",
            "/docs",
            "/redoc",
            "/favicon.ico",
            "/.well-known/*",
            "/oauth/*",  # OAuth endpoints need to handle their own auth
        ],
        description="Public endpoints that skip authentication",
    )

    def validate_config(self) -> List[str]:
        """Validate configuration and return any errors.

        Returns:
            List of error messages, empty if valid
        """
        errors = []

        # Check encryption key if credential storage is enabled
        if self.enable_credential_storage and not self.kratos.encryption_key:
            errors.append(
                "Encryption key is required when credential storage is enabled"
            )

        # Check OAuth provider configuration
        for provider_name, provider_config in self.oauth_providers.items():
            if not provider_config.client_id or not provider_config.client_secret:
                errors.append(
                    f"Provider {provider_name} missing client_id or client_secret"
                )

        return errors

    def get_provider_config(self, provider_name: str) -> Optional[OAuthProviderConfig]:
        """Get OAuth provider configuration by name.

        Args:
            provider_name: Provider name

        Returns:
            Provider configuration or None if not found
        """
        return self.oauth_providers.get(provider_name.lower())
