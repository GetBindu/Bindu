"""Minimal tests for result processor."""

import pytest

from bindu.server.workers.helpers.result_processor import ResultProcessor


class TestResultProcessor:
    """Test result processor functionality."""

    @pytest.mark.asyncio
    async def test_collect_results_with_direct_value(self):
        """Test collecting direct return value."""
        result = "Direct response"

        collected = await ResultProcessor.collect_results(result)

        assert collected == "Direct response"

    @pytest.mark.asyncio
    async def test_collect_results_with_dict(self):
        """Test collecting dict result."""
        result = {"message": "Hello", "data": 123}

        collected = await ResultProcessor.collect_results(result)

        assert collected == {"message": "Hello", "data": 123}

    @pytest.mark.asyncio
    async def test_collect_results_with_async_generator(self):
        """Test collecting from async generator."""

        async def async_gen():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        collected = await ResultProcessor.collect_results(async_gen())

        assert collected == "chunk3"

    @pytest.mark.asyncio
    async def test_collect_results_with_sync_generator(self):
        """Test collecting from sync generator."""

        def sync_gen():
            yield "item1"
            yield "item2"
            yield "item3"

        collected = await ResultProcessor.collect_results(sync_gen())

        assert collected == "item3"

    @pytest.mark.asyncio
    async def test_collect_results_with_empty_async_generator(self):
        """Test collecting from empty async generator."""

        async def empty_gen():
            return
            yield

        collected = await ResultProcessor.collect_results(empty_gen())

        assert collected is None

    def test_normalize_result_with_dict(self):
        """Test normalizing dict result."""
        result = {"response": "Hello world"}

        normalized = ResultProcessor.normalize_result(result)

        assert normalized == {"response": "Hello world"}

    def test_normalize_result_with_string(self):
        """Test normalizing string result."""
        result = "Simple string response"

        normalized = ResultProcessor.normalize_result(result)

        assert normalized == "Simple string response"

    def test_normalize_result_with_list_extracts_last_content(self):
        """Test normalizing list result extracts content from last item."""
        # Simulate list of message-like objects
        result = [{"content": "item1"}, {"content": "item2"}, {"content": "item3"}]

        normalized = ResultProcessor.normalize_result(result)

        # Should extract content from last item
        assert normalized == "item3"

    def test_normalize_result_with_none(self):
        """Test normalizing None result returns empty string."""
        result = None

        normalized = ResultProcessor.normalize_result(result)

        # None is converted to empty string
        assert normalized == ""

    @pytest.mark.asyncio
    async def test_collect_results_with_empty_sync_generator(self):
        """Test collecting from empty sync generator."""

        def empty_gen():
            return
            yield

        collected = await ResultProcessor.collect_results(empty_gen())

        assert collected is None
