"""Unit tests for Vault integration with DID keys and Hydra credentials."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bindu.common.models import AgentCredentials
from bindu.utils.vault_client import (
    VaultClient,
    backup_did_keys_to_vault,
    restore_did_keys_from_vault,
)


@pytest.fixture
def mock_vault_settings():
    """Mock Vault settings."""
    with patch("bindu.utils.vault_client.app_settings") as mock_settings:
        mock_settings.vault.enabled = True
        mock_settings.vault.url = "http://localhost:8200"
        mock_settings.vault.token = "test-token"  # pragma: allowlist secret
        mock_settings.did.private_key_filename = (
            "private.pem"  # pragma: allowlist secret
        )
        mock_settings.did.public_key_filename = "public.pem"  # pragma: allowlist secret
        yield mock_settings


@pytest.fixture
def sample_credentials():
    """Sample agent credentials."""
    return AgentCredentials(
        agent_id="test-agent-123",
        client_id="did:bindu:alice:test-agent",
        client_secret="test-secret-abc123",  # pragma: allowlist secret
        created_at="2026-01-01T00:00:00Z",
        scopes=["openid", "offline", "agent:read", "agent:write"],
    )


@pytest.mark.asyncio
async def test_vault_client_initialization(mock_vault_settings):
    """Test VaultClient initialization."""
    client = VaultClient()

    assert client.vault_url == "http://localhost:8200"
    assert client.vault_token == "test-token"
    assert client.enabled is True


@pytest.mark.asyncio
async def test_vault_client_disabled():
    """Test VaultClient when disabled."""
    with patch("bindu.utils.vault_client.app_settings") as mock_settings:
        mock_settings.vault.enabled = False
        mock_settings.vault.token = ""

        client = VaultClient()
        assert client.enabled is False


@pytest.mark.asyncio
async def test_store_did_keys(mock_vault_settings):
    """Test storing DID keys in Vault."""
    client = VaultClient()

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"data": {"version": 1}}

        result = await client.store_did_keys(
            agent_id="test-agent-123",
            private_key_pem="-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",  # pragma: allowlist secret
            public_key_pem="-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",
            did="did:bindu:alice:test-agent",
        )

        assert result is True
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "bindu/agents/test-agent-123/did-keys" in call_args[0][1]


@pytest.mark.asyncio
async def test_get_did_keys(mock_vault_settings):
    """Test retrieving DID keys from Vault."""
    client = VaultClient()

    mock_response = {
        "data": {
            "data": {
                "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",  # pragma: allowlist secret
                "public_key": "-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----",  # pragma: allowlist secret
                "did": "did:bindu:alice:test-agent",
            }
        }
    }

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        keys = await client.get_did_keys("test-agent-123")

        assert keys is not None
        assert keys["did"] == "did:bindu:alice:test-agent"
        assert "private_key" in keys
        assert "public_key" in keys


@pytest.mark.asyncio
async def test_get_did_keys_not_found(mock_vault_settings):
    """Test retrieving non-existent DID keys."""
    client = VaultClient()

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = None

        keys = await client.get_did_keys("non-existent-agent")

        assert keys is None


@pytest.mark.asyncio
async def test_store_hydra_credentials(mock_vault_settings, sample_credentials):
    """Test storing Hydra credentials in Vault."""
    client = VaultClient()

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"data": {"version": 1}}

        result = await client.store_hydra_credentials(sample_credentials)

        assert result is True
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "bindu/hydra/credentials" in call_args[0][1]
        assert sample_credentials.client_id in call_args[0][1]


@pytest.mark.asyncio
async def test_get_hydra_credentials(mock_vault_settings, sample_credentials):
    """Test retrieving Hydra credentials from Vault."""
    client = VaultClient()

    mock_response = {"data": {"data": sample_credentials.to_dict()}}

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response

        creds = await client.get_hydra_credentials(sample_credentials.client_id)

        assert creds is not None
        assert creds.client_id == sample_credentials.client_id
        assert creds.client_secret == sample_credentials.client_secret
        assert creds.agent_id == sample_credentials.agent_id


@pytest.mark.asyncio
async def test_get_hydra_credentials_not_found(mock_vault_settings):
    """Test retrieving non-existent Hydra credentials."""
    client = VaultClient()

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = None

        creds = await client.get_hydra_credentials("did:bindu:alice:non-existent")

        assert creds is None


@pytest.mark.asyncio
async def test_restore_did_keys_from_vault(mock_vault_settings, tmp_path):
    """Test restoring DID keys from Vault to filesystem."""
    mock_keys = {
        "private_key": "-----BEGIN PRIVATE KEY-----\ntest-private\n-----END PRIVATE KEY-----",  # pragma: allowlist secret
        "public_key": "-----BEGIN PUBLIC KEY-----\ntest-public\n-----END PUBLIC KEY-----",  # pragma: allowlist secret
        "did": "did:bindu:alice:test-agent",
    }

    with patch("bindu.utils.vault_client.VaultClient") as mock_vault_class:
        mock_vault = AsyncMock()
        mock_vault.get_did_keys.return_value = mock_keys
        mock_vault_class.return_value = mock_vault

        key_dir = tmp_path / "keys"
        did = await restore_did_keys_from_vault("test-agent-123", key_dir)

        assert did == "did:bindu:alice:test-agent"
        assert (key_dir / "private.pem").exists()
        assert (key_dir / "public.pem").exists()

        # Verify file contents
        with open(key_dir / "private.pem", "r") as f:
            assert f.read() == mock_keys["private_key"]

        with open(key_dir / "public.pem", "r") as f:
            assert f.read() == mock_keys["public_key"]


@pytest.mark.asyncio
async def test_restore_did_keys_not_found(mock_vault_settings, tmp_path):
    """Test restoring DID keys when not found in Vault."""
    with patch("bindu.utils.vault_client.VaultClient") as mock_vault_class:
        mock_vault = AsyncMock()
        mock_vault.get_did_keys.return_value = None
        mock_vault_class.return_value = mock_vault

        key_dir = tmp_path / "keys"
        did = await restore_did_keys_from_vault("non-existent-agent", key_dir)

        assert did is None


@pytest.mark.asyncio
async def test_backup_did_keys_to_vault(mock_vault_settings, tmp_path):
    """Test backing up DID keys from filesystem to Vault."""
    # Create test key files
    key_dir = tmp_path / "keys"
    key_dir.mkdir(parents=True)

    private_key_content = "-----BEGIN PRIVATE KEY-----\ntest-private\n-----END PRIVATE KEY-----"  # pragma: allowlist secret
    public_key_content = "-----BEGIN PUBLIC KEY-----\ntest-public\n-----END PUBLIC KEY-----"  # pragma: allowlist secret

    with open(key_dir / "private.pem", "w") as f:
        f.write(private_key_content)

    with open(key_dir / "public.pem", "w") as f:
        f.write(public_key_content)

    with patch("bindu.utils.vault_client.VaultClient") as mock_vault_class:
        mock_vault = AsyncMock()
        mock_vault.store_did_keys.return_value = True
        mock_vault_class.return_value = mock_vault

        result = await backup_did_keys_to_vault(
            agent_id="test-agent-123",
            key_dir=key_dir,
            did="did:bindu:alice:test-agent",
        )

        assert result is True
        mock_vault.store_did_keys.assert_called_once_with(
            agent_id="test-agent-123",
            private_key_pem=private_key_content,
            public_key_pem=public_key_content,
            did="did:bindu:alice:test-agent",
        )


@pytest.mark.asyncio
async def test_backup_did_keys_missing_files(mock_vault_settings, tmp_path):
    """Test backing up DID keys when files don't exist."""
    key_dir = tmp_path / "keys"

    result = await backup_did_keys_to_vault(
        agent_id="test-agent-123",
        key_dir=key_dir,
        did="did:bindu:alice:test-agent",
    )

    assert result is False


@pytest.mark.asyncio
async def test_vault_client_disabled_operations(mock_vault_settings):
    """Test Vault operations when disabled."""
    with patch("bindu.utils.vault_client.app_settings") as mock_settings:
        mock_settings.vault.enabled = False
        mock_settings.vault.token = ""

        client = VaultClient()

        # All operations should return None/False when disabled
        assert await client.store_did_keys("agent", "priv", "pub", "did") is False
        assert await client.get_did_keys("agent") is None
        assert await client.store_hydra_credentials(MagicMock()) is False
        assert await client.get_hydra_credentials("did") is None
