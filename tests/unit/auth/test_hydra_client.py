"""Tests for Hydra OAuth2 client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bindu.auth.hydra.client import HydraClient


class TestHydraClientInitialization:
    """Test HydraClient initialization and configuration."""

    def test_init_with_admin_url_only(self):
        """Test initialization with only admin URL derives public URL."""
        client = HydraClient(admin_url="http://localhost:4445")

        assert client.admin_url == "http://localhost:4445"
        assert client.public_url == "http://localhost:4444"

    def test_init_with_both_urls(self):
        """Test initialization with both admin and public URLs."""
        client = HydraClient(
            admin_url="http://hydra-admin:4445", public_url="http://hydra-public:4444"
        )

        assert client.admin_url == "http://hydra-admin:4445"
        assert client.public_url == "http://hydra-public:4444"

    def test_init_strips_trailing_slashes(self):
        """Test that trailing slashes are removed from URLs."""
        client = HydraClient(
            admin_url="http://localhost:4445/", public_url="http://localhost:4444/"
        )

        assert client.admin_url == "http://localhost:4445"
        assert client.public_url == "http://localhost:4444"

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = HydraClient(admin_url="http://localhost:4445", timeout=30)
        assert client._http_client.timeout == 30

    def test_init_with_ssl_verification_disabled(self):
        """Test initialization with SSL verification disabled."""
        client = HydraClient(admin_url="http://localhost:4445", verify_ssl=False)
        assert client._http_client.verify_ssl is False

    def test_init_with_custom_retries(self):
        """Test initialization with custom retry count."""
        client = HydraClient(admin_url="http://localhost:4445", max_retries=5)
        assert client._http_client.max_retries == 5


class TestHydraClientContextManager:
    """Test HydraClient async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        """Test async context manager enters and exits properly."""
        client = HydraClient(admin_url="http://localhost:4445")

        with patch.object(
            client._http_client, "_ensure_session", new_callable=AsyncMock
        ):
            with patch.object(client, "close", new_callable=AsyncMock) as mock_close:
                async with client as ctx_client:
                    assert ctx_client is client

                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test close method closes HTTP client."""
        client = HydraClient(admin_url="http://localhost:4445")

        with patch.object(
            client._http_client, "close", new_callable=AsyncMock
        ) as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestHydraClientTokenIntrospection:
    """Test token introspection functionality."""

    @pytest.mark.asyncio
    async def test_introspect_token_success(self):
        """Test successful token introspection."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "active": True,
                "sub": "user-123",
                "scope": "read write",
                "client_id": "test-client",
            }
        )

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.introspect_token("test-token")

            assert result["active"] is True
            assert result["sub"] == "user-123"
            assert result["scope"] == "read write"

    @pytest.mark.asyncio
    async def test_introspect_token_inactive(self):
        """Test introspection of inactive token."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"active": False})

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.introspect_token("expired-token")

            assert result["active"] is False

    @pytest.mark.asyncio
    async def test_introspect_token_http_error(self):
        """Test token introspection with HTTP error."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with pytest.raises(ValueError, match="Hydra introspection failed"):
                await client.introspect_token("invalid-token")

    @pytest.mark.asyncio
    async def test_introspect_token_network_error(self):
        """Test token introspection with network error."""
        client = HydraClient(admin_url="http://localhost:4445")

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            with pytest.raises(ValueError, match="Failed to introspect token"):
                await client.introspect_token("test-token")


class TestHydraClientOAuthManagement:
    """Test OAuth2 client management operations."""

    @pytest.mark.asyncio
    async def test_create_oauth_client_success(self):
        """Test successful OAuth client creation."""
        client = HydraClient(admin_url="http://localhost:4445")

        client_data = {
            "client_id": "test-client",
            "client_secret": "secret",
            "grant_types": ["client_credentials"],
        }

        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value=client_data)

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.create_oauth_client(client_data)

            assert result["client_id"] == "test-client"

    @pytest.mark.asyncio
    async def test_create_oauth_client_failure(self):
        """Test OAuth client creation failure."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Invalid client data")

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with pytest.raises(ValueError, match="Failed to create OAuth client"):
                await client.create_oauth_client({})

    @pytest.mark.asyncio
    async def test_get_oauth_client_found(self):
        """Test getting existing OAuth client."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"client_id": "test-client"})

        with patch.object(
            client._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.get_oauth_client("test-client")

            assert result is not None
            assert result["client_id"] == "test-client"

    @pytest.mark.asyncio
    async def test_get_oauth_client_not_found(self):
        """Test getting non-existent OAuth client returns None."""
        client = HydraClient(admin_url="http://localhost:4445")

        from bindu.utils.exceptions import HTTPClientError

        # Create HTTPClientError with proper initialization
        error = HTTPClientError(status=404, message="Not found")

        with patch.object(
            client._http_client, "get", new_callable=AsyncMock, side_effect=error
        ):
            result = await client.get_oauth_client("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_oauth_client_with_did_encoding(self):
        """Test getting OAuth client with DID (special characters encoded)."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"client_id": "did:bindu:test"})

        with patch.object(
            client._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_get:
            await client.get_oauth_client("did:bindu:test")

            # Verify URL encoding happened
            call_args = mock_get.call_args[0][0]
            assert "did%3Abindu%3Atest" in call_args

    @pytest.mark.asyncio
    async def test_list_oauth_clients_success(self):
        """Test listing OAuth clients."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[{"client_id": "client-1"}, {"client_id": "client-2"}]
        )

        with patch.object(
            client._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.list_oauth_clients(limit=10, offset=0)

            assert len(result) == 2
            assert result[0]["client_id"] == "client-1"

    @pytest.mark.asyncio
    async def test_delete_oauth_client_success(self):
        """Test successful OAuth client deletion."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 204

        with patch.object(
            client._http_client,
            "delete",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.delete_oauth_client("test-client")

            assert result is True

    @pytest.mark.asyncio
    async def test_delete_oauth_client_not_found(self):
        """Test deleting non-existent OAuth client returns False."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 404

        with patch.object(
            client._http_client,
            "delete",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.delete_oauth_client("nonexistent")

            assert result is False


class TestHydraClientHealthAndUtilities:
    """Test health check and utility methods."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when Hydra is healthy."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200

        with patch.object(
            client._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check when Hydra is unhealthy."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 503

        with patch.object(
            client._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_network_error(self):
        """Test health check with network error returns False."""
        client = HydraClient(admin_url="http://localhost:4445")

        with patch.object(
            client._http_client,
            "get",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_get_jwks_success(self):
        """Test getting JWKS successfully."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_jwks = {"keys": [{"kty": "RSA", "kid": "key-1"}]}
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_jwks)

        with patch.object(
            client._http_client,
            "get",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.get_jwks()

            assert "keys" in result
            assert len(result["keys"]) == 1

    @pytest.mark.asyncio
    async def test_revoke_token_success(self):
        """Test successful token revocation."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.revoke_token("test-token")

            assert result is True

    @pytest.mark.asyncio
    async def test_get_public_key_from_client_success(self):
        """Test getting public key from client metadata."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_client_data = {
            "client_id": "did:bindu:test",
            "metadata": {
                "public_key": "z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"
            },
        }

        with patch.object(
            client,
            "get_oauth_client",
            new_callable=AsyncMock,
            return_value=mock_client_data,
        ):
            result = await client.get_public_key_from_client("did:bindu:test")

            assert result == "z6MkpTHR8VNsBxYAAWHut2Geadd9jSwuBV8xRoAnwWsdvktH"

    @pytest.mark.asyncio
    async def test_get_public_key_from_client_not_found(self):
        """Test getting public key when client doesn't exist."""
        client = HydraClient(admin_url="http://localhost:4445")

        with patch.object(
            client, "get_oauth_client", new_callable=AsyncMock, return_value=None
        ):
            result = await client.get_public_key_from_client("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_public_key_from_client_no_key_in_metadata(self):
        """Test getting public key when metadata doesn't contain key."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_client_data = {"client_id": "did:bindu:test", "metadata": {}}

        with patch.object(
            client,
            "get_oauth_client",
            new_callable=AsyncMock,
            return_value=mock_client_data,
        ):
            result = await client.get_public_key_from_client("did:bindu:test")

            assert result is None


class TestHydraClientEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_introspect_empty_token(self):
        """Test introspecting empty token."""
        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Token required")

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            with pytest.raises(ValueError):
                await client.introspect_token("")

    @pytest.mark.asyncio
    async def test_create_client_with_special_characters_in_did(self):
        """Test creating client with DID containing special characters."""
        client = HydraClient(admin_url="http://localhost:4445")

        client_data = {
            "client_id": "did:bindu:agent:test-123",
            "client_secret": "secret",
        }

        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.json = AsyncMock(return_value=client_data)

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await client.create_oauth_client(client_data)

            assert result["client_id"] == "did:bindu:agent:test-123"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test multiple concurrent operations."""
        import asyncio

        client = HydraClient(admin_url="http://localhost:4445")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"active": True})

        with patch.object(
            client._http_client,
            "post",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            # Run multiple introspections concurrently
            results = await asyncio.gather(
                client.introspect_token("token1"),
                client.introspect_token("token2"),
                client.introspect_token("token3"),
            )

            assert len(results) == 3
            assert all(r["active"] for r in results)
