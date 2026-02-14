"""Tests for Ory configuration models."""

from bindu.settings import OAuthProviderConfig


class TestOAuthProviderConfig:
    """Test OAuth provider configuration."""

    def test_provider_config(self):
        """Test OAuth provider configuration."""
        config = OAuthProviderConfig(
            name="github",
            client_id="test_id",  # pragma: allowlist secret
            client_secret="test_secret",  # pragma: allowlist secret
            auth_url="https://github.com/login/oauth/authorize",  # type: ignore[arg-type]
            token_url="https://github.com/login/oauth/access_token",  # type: ignore[arg-type]
            scope="read:user",
            redirect_uri="http://localhost:3000/callback",  # type: ignore[arg-type]
        )
        assert config.name == "github"
