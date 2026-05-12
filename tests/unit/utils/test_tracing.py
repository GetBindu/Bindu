"""Tests for tracing utilities."""

from bindu.utils.tracing import get_trace_context


class TestTracing:
    """Test tracing utility functions."""

    def test_get_trace_context_returns_tuple(self):
        """Test getting trace context returns a tuple."""
        trace_id, span_id = get_trace_context()

        # Should return tuple of (trace_id, span_id) or (None, None)
        assert trace_id is None or isinstance(trace_id, str)
        assert span_id is None or isinstance(span_id, str)

    def test_get_trace_context_without_active_span(self):
        """Test getting trace context without active span."""
        trace_id, span_id = get_trace_context()

        # Without an active span, should return (None, None)
        assert trace_id is None
        assert span_id is None

    def test_get_trace_context_with_exception(self):
        """Test getting trace context when exception occurs."""
        from unittest.mock import patch

        # Mock get_current_span to raise an exception
        with patch("bindu.utils.tracing.get_current_span") as mock_span:
            mock_span.side_effect = RuntimeError("Test error")
            trace_id, span_id = get_trace_context()

            # Should return (None, None) on exception
            assert trace_id is None
            assert span_id is None

    def test_get_trace_context_with_invalid_span(self):
        """Test getting trace context with invalid span."""
        from unittest.mock import Mock, patch

        # Mock get_current_span to return an invalid span
        with patch("bindu.utils.tracing.get_current_span") as mock_span:
            mock_span_instance = Mock()
            mock_span_instance.get_span_context.return_value = Mock(is_valid=False)
            mock_span.return_value = mock_span_instance

            trace_id, span_id = get_trace_context()

            # Should return (None, None) for invalid span
            assert trace_id is None
            assert span_id is None

    def test_get_trace_context_with_valid_span(self):
        """Test getting trace context with valid span."""
        from unittest.mock import Mock, patch

        # Mock get_current_span to return a valid span
        with patch("bindu.utils.tracing.get_current_span") as mock_span:
            mock_span_instance = Mock()
            ctx = Mock()
            ctx.is_valid = True
            ctx.trace_id = 12345
            ctx.span_id = 67890
            mock_span_instance.get_span_context.return_value = ctx
            mock_span.return_value = mock_span_instance

            trace_id, span_id = get_trace_context()

            # Should return valid trace and span IDs
            assert trace_id is not None
            assert span_id is not None

    def test_get_trace_context_with_none_span(self):
        """Test getting trace context when span is None."""
        from unittest.mock import patch

        # Mock get_current_span to return None
        with patch("bindu.utils.tracing.get_current_span") as mock_span:
            mock_span.return_value = None

            trace_id, span_id = get_trace_context()

            # Should return (None, None) when span is None
            assert trace_id is None
            assert span_id is None
