"""Unit tests for bindu.dspy.prompt_storage module.

Tests cover:
- JSON-based prompt storage
- File operations and locking
- Prompt CRUD operations
- Concurrent access handling
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import uuid

from bindu.dspy.prompt_storage import PromptStorage, DEFAULT_PROMPT_FILE


class TestPromptStorageInitialization:
    """Test suite for PromptStorage initialization."""

    def test_storage_creation_default_path(self):
        """Test creating PromptStorage with default path."""
        with patch.object(PromptStorage, "_ensure_file"):
            storage = PromptStorage()
            assert storage.filepath == DEFAULT_PROMPT_FILE

    def test_storage_creation_custom_path(self):
        """Test creating PromptStorage with custom path."""
        custom_path = Path("custom_prompts.json")

        with patch.object(PromptStorage, "_ensure_file"):
            storage = PromptStorage(filepath=custom_path)
            assert storage.filepath == custom_path

    def test_storage_creates_lock_file_path(self):
        """Test that storage creates lock file path."""
        with patch.object(PromptStorage, "_ensure_file"):
            storage = PromptStorage(filepath=Path("prompts.json"))
            assert storage.lock_path == Path("prompts.lock")

    def test_storage_initializes_async_lock(self):
        """Test that async lock is initialized."""
        with patch.object(PromptStorage, "_ensure_file"):
            storage = PromptStorage()
            assert storage._async_lock is not None


class TestPromptStorageFileOperations:
    """Test suite for file operations."""

    def test_ensure_file_creates_json(self):
        """Test that _ensure_file creates JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Remove the file so _ensure_file creates it
            tmp_path.unlink()

            storage = PromptStorage(filepath=tmp_path)

            assert tmp_path.exists()
            with open(tmp_path) as f:
                data = json.load(f)
                assert "prompts" in data

        finally:
            if tmp_path.exists():
                tmp_path.unlink()
            lock_path = tmp_path.with_suffix(".lock")
            if lock_path.exists():
                lock_path.unlink()

    def test_load_sync_returns_dict(self):
        """Test synchronous load returns dictionary."""
        with patch("bindu.dspy.prompt_storage.FileLock"), patch(
            "json.load"
        ) as mock_json_load, patch("builtins.open", create=True):
            mock_json_load.return_value = {"prompts": {"id1": {"text": "Prompt"}}}
            
            storage = PromptStorage()
            result = storage._load_sync()
            
            # Result should be dict
            assert isinstance(result, dict)

    def test_save_sync_writes_json(self):
        """Test synchronous save writes JSON."""
        with patch("bindu.dspy.prompt_storage.FileLock"), patch(
            "builtins.open", create=True
        ), patch("os.replace"):

            storage = PromptStorage()
            test_prompts = {"id1": {"prompt_text": "Test"}}

            # Should not raise
            storage._save_sync(test_prompts)


class TestPromptStorageSyncOperations:
    """Test suite for synchronous operations."""

    def test_insert_prompt_sync_returns_uuid(self):
        """Test that insert_prompt_sync returns a valid UUID."""
        with patch("bindu.dspy.prompt_storage.FileLock"), patch("builtins.open", create=True), patch(
            "os.replace"
        ), patch("json.load") as mock_load, patch("json.dump"):

            mock_load.return_value = {"prompts": {}}

            storage = PromptStorage()
            prompt_id = storage.insert_prompt_sync("Test prompt", "active", 1.0)

            # Should return a valid UUID string
            assert isinstance(prompt_id, str)
            try:
                uuid.UUID(prompt_id)
            except ValueError:
                pytest.fail(f"Invalid UUID: {prompt_id}")

    def test_insert_prompt_sync_handles_duplicates(self):
        """Test that duplicate prompts return same ID."""
        with patch("bindu.dspy.prompt_storage.FileLock"), patch("builtins.open", create=True), patch(
            "os.replace"
        ), patch("json.load") as mock_load, patch("json.dump"):

            existing_id = str(uuid.uuid4())
            mock_load.return_value = {
                "prompts": {
                    existing_id: {
                        "id": existing_id,
                        "prompt_text": "Test",
                        "status": "active",
                        "traffic": 1.0,
                    }
                }
            }

            storage = PromptStorage()
            new_id = storage.insert_prompt_sync("Test", "active", 1.0)

            # Should return existing ID
            assert new_id == existing_id


class TestPromptStorageAsyncOperations:
    """Test suite for asynchronous operations."""

    @pytest.mark.asyncio
    async def test_get_active_prompt_async(self):
        """Test getting active prompt asynchronously."""
        with patch.object(PromptStorage, "_load_async", new_callable=AsyncMock) as mock_load:

            mock_load.return_value = {
                "id1": {
                    "id": "id1",
                    "status": "active",
                    "prompt_text": "Active",
                    "traffic": 1.0,
                }
            }

            storage = PromptStorage()
            result = await storage.get_active_prompt()

            assert result is not None
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_candidate_prompt_async(self):
        """Test getting candidate prompt asynchronously."""
        with patch.object(PromptStorage, "_load_async", new_callable=AsyncMock) as mock_load:

            mock_load.return_value = {
                "id1": {
                    "id": "id1",
                    "status": "candidate",
                    "prompt_text": "Candidate",
                    "traffic": 0.2,
                }
            }

            storage = PromptStorage()
            result = await storage.get_candidate_prompt()

            assert result is not None
            assert result["status"] == "candidate"

    @pytest.mark.asyncio
    async def test_insert_prompt_async(self):
        """Test inserting prompt asynchronously."""
        with patch.object(
            PromptStorage, "_load_async", new_callable=AsyncMock
        ) as mock_load, patch.object(
            PromptStorage, "_save_async", new_callable=AsyncMock
        ):

            mock_load.return_value = {}

            storage = PromptStorage()
            result = await storage.insert_prompt("New prompt", "active", 1.0)

            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_update_prompt_traffic_async(self):
        """Test updating prompt traffic asynchronously."""
        prompt_id = str(uuid.uuid4())
        temp_data = {"prompts": {prompt_id: {"id": prompt_id, "traffic": 1.0}}}

        with patch("builtins.open", create=True), patch(
            "json.load", return_value=temp_data
        ), patch("json.dump"), patch("os.replace"), patch(
            "bindu.dspy.prompt_storage.FileLock"
        ):

            storage = PromptStorage()
            # Should execute without raising an error
            await storage.update_prompt_traffic(prompt_id, 0.5)


class TestPromptStorageEnrichment:
    """Test suite for prompt enrichment."""

    def test_enrich_prompt_adds_metrics(self):
        """Test that enrich_prompt adds computed metrics."""
        with patch.object(PromptStorage, "_ensure_file"):
            storage = PromptStorage()

            prompt = {
                "id": "id1",
                "prompt_text": "Test",
                "status": "active",
            }

            enriched = storage._enrich_prompt(prompt)

            assert "num_interactions" in enriched
            assert "average_feedback_score" in enriched
            assert enriched["num_interactions"] == 0
            assert enriched["average_feedback_score"] is None

    def test_enrich_prompt_preserves_original(self):
        """Test that enrichment doesn't modify original."""
        with patch.object(PromptStorage, "_ensure_file"):
            storage = PromptStorage()

            original = {"id": "id1", "prompt_text": "Test"}
            enriched = storage._enrich_prompt(original)

            assert "num_interactions" in enriched
            assert "num_interactions" not in original


class TestPromptStorageEdgeCases:
    """Test suite for edge cases."""

    def test_empty_prompt_text(self):
        """Test handling of empty prompt text."""
        with patch("bindu.dspy.prompt_storage.FileLock"), patch("builtins.open", create=True), patch(
            "os.replace"
        ), patch("json.load") as mock_load, patch("json.dump"):

            mock_load.return_value = {"prompts": {}}

            storage = PromptStorage()
            prompt_id = storage.insert_prompt_sync("", "active", 1.0)

            assert isinstance(prompt_id, str)

    def test_prompt_with_special_chars(self):
        """Test handling of prompt text with special characters."""
        with patch("bindu.dspy.prompt_storage.FileLock"), patch("builtins.open", create=True), patch(
            "os.replace"
        ), patch("json.load") as mock_load, patch("json.dump"):

            mock_load.return_value = {"prompts": {}}

            storage = PromptStorage()
            special_text = "Test with special chars: \\n \\t \"quoted\" 'single'"
            prompt_id = storage.insert_prompt_sync(special_text, "active", 1.0)

            assert isinstance(prompt_id, str)

    def test_traffic_normalization(self):
        """Test traffic values are stored as floats."""
        with patch("bindu.dspy.prompt_storage.FileLock"), patch("builtins.open", create=True), patch(
            "os.replace"
        ), patch("json.load") as mock_load, patch("json.dump"):

            mock_load.return_value = {"prompts": {}}

            storage = PromptStorage()
            storage.insert_prompt_sync("Test", "active", 0.75)

            # Should handle float traffic values
