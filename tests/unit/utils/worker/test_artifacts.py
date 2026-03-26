"""Tests for worker artifact utilities."""

from unittest.mock import Mock

from bindu.utils.worker.artifacts import ArtifactBuilder


class TestArtifactBuilder:
    """Test ArtifactBuilder functionality."""

    def test_from_result_with_string(self):
        """Test creating artifact from string result."""
        result = "Task completed successfully"

        artifacts = ArtifactBuilder.from_result(result)

        assert len(artifacts) == 1
        assert "artifact_id" in artifacts[0]
        assert "name" in artifacts[0]
        assert len(artifacts[0]["parts"]) == 1
        assert artifacts[0]["parts"][0]["kind"] == "text"
        assert artifacts[0]["parts"][0]["text"] == result

    def test_from_result_with_dict(self):
        """Test creating artifact from dict result."""
        result = {"status": "success", "data": {"key": "value"}}

        artifacts = ArtifactBuilder.from_result(result)

        assert len(artifacts) == 1
        assert "artifact_id" in artifacts[0]
        assert len(artifacts[0]["parts"]) == 1
        assert artifacts[0]["parts"][0]["kind"] == "data"

    def test_from_result_with_list_of_strings(self):
        """Test creating artifact from list of strings."""
        result = ["item1", "item2", "item3"]

        artifacts = ArtifactBuilder.from_result(result)

        assert len(artifacts) == 1
        assert "artifact_id" in artifacts[0]
        assert len(artifacts[0]["parts"]) == 1
        # List of strings should be joined
        assert artifacts[0]["parts"][0]["kind"] == "text"

    def test_from_result_with_did_extension(self):
        """Test creating artifact with DID extension."""
        mock_did_extension = Mock()
        mock_did_extension.did = "did:example:123"
        mock_did_extension.sign_text = Mock(return_value={"signature": "sig123"})

        result = "Signed result"

        artifacts = ArtifactBuilder.from_result(result, did_extension=mock_did_extension)

        assert len(artifacts) == 1
        # DID extension should be used for signing text
        mock_did_extension.sign_text.assert_called_once_with("Signed result")

    def test_from_result_with_empty_string(self):
        """Test creating artifact from empty string."""
        result = ""

        artifacts = ArtifactBuilder.from_result(result)

        assert len(artifacts) == 1
        assert artifacts[0]["parts"][0]["text"] == ""

    def test_from_result_with_none(self):
        """Test creating artifact from None."""
        result = None

        artifacts = ArtifactBuilder.from_result(result)

        assert len(artifacts) >= 1  # Should handle None gracefully
        assert "artifact_id" in artifacts[0]

    def test_from_result_with_custom_name(self):
        """Test creating artifact with custom name."""
        result = "test"

        artifacts = ArtifactBuilder.from_result(result, artifact_name="custom_result")

        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "custom_result"
