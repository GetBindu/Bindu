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
