"""Minimal tests for skill embedder."""

import pytest
from unittest.mock import patch

from bindu.server.negotiation.embedder import SkillEmbedder


class TestSkillEmbedder:
    """Test skill embedder functionality."""

    def test_embedder_initialization_with_api_key(self):
        """Test embedder initialization with API key."""
        embedder = SkillEmbedder(api_key="test-key-123")

        assert embedder._api_key == "test-key-123"
        assert embedder._client is None

    def test_embedder_initialization_without_api_key(self):
        """Test embedder initialization falls back to settings."""
        with patch("bindu.server.negotiation.embedder.app_settings") as mock_settings:
            mock_settings.negotiation.embedding_api_key = "settings-key"
            mock_settings.negotiation.embedding_model = "test-model"
            mock_settings.negotiation.embedding_provider = "openrouter"

            embedder = SkillEmbedder()

            assert embedder._api_key == "settings-key"

    def test_get_client_creates_client(self):
        """Test that get_client creates AsyncHTTPClient."""
        embedder = SkillEmbedder(api_key="test-key")

        with patch("bindu.server.negotiation.embedder.AsyncHTTPClient") as mock_client:
            embedder._get_client()

            mock_client.assert_called_once()
            assert embedder._client is not None

    def test_get_client_reuses_existing_client(self):
        """Test that get_client reuses existing client."""
        embedder = SkillEmbedder(api_key="test-key")

        with patch("bindu.server.negotiation.embedder.AsyncHTTPClient") as mock_client:
            client1 = embedder._get_client()
            client2 = embedder._get_client()

            # Should only create once
            assert mock_client.call_count == 1
            assert client1 is client2

    @pytest.mark.asyncio
    async def test_embed_without_api_key_raises(self):
        """Test that embedding without API key raises error."""
        embedder = SkillEmbedder(api_key=None)

        with patch("bindu.server.negotiation.embedder.app_settings") as mock_settings:
            mock_settings.negotiation.embedding_api_key = None
            embedder._api_key = None

            with pytest.raises(ValueError, match="API key not configured"):
                await embedder._embed_with_openrouter(["test text"])
