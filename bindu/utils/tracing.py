"""Tracing utilities for OpenTelemetry integration."""

from __future__ import annotations

from opentelemetry.trace import get_current_span


def get_trace_context() -> tuple[str | None, str | None]:
    """Extract primitive trace context from the live OpenTelemetry span.

    Returns:
        Tuple of (trace_id, span_id) as hex strings, or (None, None) if no valid span
    """
    try:
        span = get_current_span()
        if span and hasattr(span, "get_span_context"):
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    except Exception:
        pass
    return None, None
