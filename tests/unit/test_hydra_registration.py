"""Tests for Hydra registration utilities."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from bindu.auth.hydra.registration import (
    save_agent_credentials,
    load_agent_credentials,
    AgentCredentials,
    register_agent_in_hydra,
)


class TestSaveAgentCredentials:
    """Test saving agent credentials."""

    def test_save_credentials_new_file(self):
        """Test saving credentials to a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)

            credentials = AgentCredentials(
                agent_id="test-agent-123",
                client_id="did:key:test123",
                client_secret="test-secret-456",  # pragma: allowlist secret
                created_at="2026-01-01T00:00:00Z",
                scopes=["agent:read", "agent:write"],
            )

            save_agent_credentials(credentials, credentials_dir)

            # Verify file was created
            creds_file = credentials_dir / "oauth_credentials.json"
            assert creds_file.exists()

            # Verify content
            with open(creds_file, "r") as f:
                saved_data = json.load(f)

            assert "did:key:test123" in saved_data
            assert saved_data["did:key:test123"]["agent_id"] == "test-agent-123"
            assert saved_data["did:key:test123"]["client_id"] == "did:key:test123"

    def test_save_credentials_append_to_existing(self):
        """Test appending credentials to existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)

            # Create first credential
            cred1 = AgentCredentials(
                agent_id="agent-1",
                client_id="did:key:first",
                client_secret="secret-1",  # pragma: allowlist secret
                created_at="2026-01-01T00:00:00Z",
                scopes=["agent:read"],
            )
            save_agent_credentials(cred1, credentials_dir)

            # Add second credential
            cred2 = AgentCredentials(
                agent_id="agent-2",
                client_id="did:key:second",
                client_secret="secret-2",  # pragma: allowlist secret
                created_at="2026-01-02T00:00:00Z",
                scopes=["agent:write"],
            )
            save_agent_credentials(cred2, credentials_dir)

            # Verify both exist
            creds_file = credentials_dir / "oauth_credentials.json"
            with open(creds_file, "r") as f:
                saved_data = json.load(f)

            assert len(saved_data) == 2
            assert "did:key:first" in saved_data
            assert "did:key:second" in saved_data

    def test_save_credentials_corrupted_file(self):
        """Test handling corrupted credentials file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)
            creds_file = credentials_dir / "oauth_credentials.json"

            # Create corrupted file
            with open(creds_file, "w") as f:
                f.write("invalid json{{{")

            # Should still save successfully
            credentials = AgentCredentials(
                agent_id="test-agent",
                client_id="did:key:test",
                client_secret="test-secret",  # pragma: allowlist secret
                created_at="2026-01-01T00:00:00Z",
                scopes=["agent:read"],
            )
            save_agent_credentials(credentials, credentials_dir)

            # Verify new valid file was created
            with open(creds_file, "r") as f:
                saved_data = json.load(f)

            assert "did:key:test" in saved_data


class TestLoadAgentCredentials:
    """Test loading agent credentials."""

    def test_load_credentials_success(self):
        """Test successfully loading credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)

            # Save credentials first
            credentials = AgentCredentials(
                agent_id="test-agent",
                client_id="did:key:test123",
                client_secret="test-secret",  # pragma: allowlist secret
                created_at="2026-01-01T00:00:00Z",
                scopes=["agent:read", "agent:write"],
            )
            save_agent_credentials(credentials, credentials_dir)

            # Load by DID
            loaded = load_agent_credentials("did:key:test123", credentials_dir)

            assert loaded is not None
            assert loaded.agent_id == "test-agent"
            assert loaded.client_id == "did:key:test123"
            assert loaded.client_secret == "test-secret"  # pragma: allowlist secret
            assert loaded.scopes == ["agent:read", "agent:write"]

    def test_load_credentials_not_found(self):
        """Test loading when DID not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)

            # Save one credential
            credentials = AgentCredentials(
                agent_id="test-agent",
                client_id="did:key:exists",
                client_secret="test-secret",  # pragma: allowlist secret
                created_at="2026-01-01T00:00:00Z",
                scopes=["agent:read"],
            )
            save_agent_credentials(credentials, credentials_dir)

            # Try to load different DID
            loaded = load_agent_credentials("did:key:notfound", credentials_dir)

            assert loaded is None

    def test_load_credentials_no_file(self):
        """Test loading when credentials file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)

            loaded = load_agent_credentials("did:key:test", credentials_dir)

            assert loaded is None

    def test_load_credentials_corrupted_file(self):
        """Test loading from corrupted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)
            creds_file = credentials_dir / "oauth_credentials.json"

            # Create corrupted file
            with open(creds_file, "w") as f:
                f.write("invalid json{{{")

            loaded = load_agent_credentials("did:key:test", credentials_dir)

            assert loaded is None

    def test_load_credentials_invalid_data(self):
        """Test loading when credential data is invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_dir = Path(tmpdir)
            creds_file = credentials_dir / "oauth_credentials.json"

            # Create file with invalid credential data
            with open(creds_file, "w") as f:
                json.dump(
                    {
                        "did:key:test": {
                            "agent_id": "test",
                            # Missing required fields
                        }
                    },
                    f,
                )

            loaded = load_agent_credentials("did:key:test", credentials_dir)

            assert loaded is None


class TestAgentCredentials:
    """Test AgentCredentials model."""

    def test_credentials_to_dict(self):
        """Test converting credentials to dict."""
        credentials = AgentCredentials(
            agent_id="test-agent",
            client_id="did:key:test",
            client_secret="test-secret",  # pragma: allowlist secret
            created_at="2026-01-01T00:00:00Z",
            scopes=["agent:read", "agent:write"],
        )

        data = credentials.to_dict()

        assert data["agent_id"] == "test-agent"
        assert data["client_id"] == "did:key:test"
        assert data["client_secret"] == "test-secret"  # pragma: allowlist secret
        assert data["created_at"] == "2026-01-01T00:00:00Z"
        assert data["scopes"] == ["agent:read", "agent:write"]

    def test_credentials_from_dict(self):
        """Test creating credentials from dict."""
        data = {
            "agent_id": "test-agent",
            "client_id": "did:key:test",
            "client_secret": "test-secret",  # pragma: allowlist secret
            "created_at": "2026-01-01T00:00:00Z",
            "scopes": ["agent:read", "agent:write"],
        }

        credentials = AgentCredentials.from_dict(data)

        assert credentials.agent_id == "test-agent"
        assert credentials.client_id == "did:key:test"
        assert credentials.client_secret == "test-secret"  # pragma: allowlist secret
        assert credentials.created_at == "2026-01-01T00:00:00Z"
        assert credentials.scopes == ["agent:read", "agent:write"]


class TestRegisterAgentInHydra:
    """Test agent registration in Hydra."""

    @pytest.mark.asyncio
    async def test_registration_disabled(self):
        """Test when auto-registration is disabled."""

        with patch("bindu.auth.hydra.registration.app_settings") as mock_settings:
            mock_settings.hydra.auto_register_agents = False

            result = await register_agent_in_hydra(
                agent_id="test-agent",
                agent_name="Test Agent",
                agent_url="http://localhost:3773",
                did="did:key:test",
                credentials_dir=Path("/tmp/.bindu"),
            )

            assert result is None
