"""External dependency stubs for testing.

This module provides lightweight stubs for external dependencies to avoid
requiring heavy optional dependencies during testing.
"""

import sys
from types import ModuleType


def setup_opentelemetry_stubs():
    """Set up OpenTelemetry stubs for testing."""
    ot_trace = ModuleType("opentelemetry.trace")

    class _Span:
        def is_recording(self):
            return True

        def add_event(self, *args, **kwargs):
            return None

        def set_attributes(self, *args, **kwargs):
            return None

        def set_attribute(self, *args, **kwargs):
            return None

        def set_status(self, *args, **kwargs):
            return None

    def get_current_span():
        return _Span()

    class _SpanCtx:
        def __enter__(self):
            return _Span()

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Tracer:
        def start_as_current_span(self, name: str, **kwargs):
            return _SpanCtx()

        def start_span(self, name: str, **kwargs):
            return _Span()

    class _StatusCode:
        OK = "OK"
        ERROR = "ERROR"

    class _Status:
        def __init__(self, *args, **kwargs):
            pass

    ot_trace.get_current_span = get_current_span  # type: ignore[attr-defined]
    ot_trace.get_tracer = lambda name: _Tracer()  # type: ignore[attr-defined]
    ot_trace.Status = _Status  # type: ignore[attr-defined]
    ot_trace.StatusCode = _StatusCode  # type: ignore[attr-defined]
    ot_trace.Span = _Span  # type: ignore[attr-defined]
    ot_trace.use_span = lambda span: _SpanCtx()  # type: ignore[attr-defined]

    # Setup metrics
    metrics_mod = ModuleType("opentelemetry.metrics")

    class _Counter:
        def add(self, *_args, **_kwargs):
            return None

    class _Histogram:
        def record(self, *_args, **_kwargs):
            return None

    class _UpDownCounter:
        def add(self, *_args, **_kwargs):
            return None

    class _Meter:
        def create_counter(self, *_args, **_kwargs):
            return _Counter()

        def create_histogram(self, *_args, **_kwargs):
            return _Histogram()

        def create_up_down_counter(self, *_args, **_kwargs):
            return _UpDownCounter()

    def get_meter(name: str):
        return _Meter()

    metrics_mod.get_meter = get_meter  # type: ignore[attr-defined]

    # Register modules
    op_root = ModuleType("opentelemetry")
    op_root.metrics = metrics_mod  # type: ignore[attr-defined]
    op_root.trace = ot_trace  # type: ignore[attr-defined]

    sys.modules["opentelemetry"] = op_root
    sys.modules["opentelemetry.trace"] = ot_trace
    sys.modules["opentelemetry.metrics"] = metrics_mod


def setup_x402_stubs():
    """Set up X402 payment extension stubs for testing."""

    class _PaymentRequirements:
        def __init__(self, **kwargs):
            self._data = kwargs

        def model_dump(self, by_alias: bool = True):
            return dict(self._data)

        def model_copy(self, update: dict | None = None):
            new_data = dict(self._data)
            if update:
                new_data.update(update)
            return _PaymentRequirements(**new_data)

    class _PaymentPayload:
        def __init__(self, **kwargs):
            self._data = kwargs

        @classmethod
        def model_validate(cls, data):
            return cls(**data) if isinstance(data, dict) else cls()

        def model_dump(self, by_alias: bool = True):
            return dict(self._data)

    class _x402PaymentRequiredResponse:
        def __init__(self, **kwargs):
            self._data = kwargs

        def model_dump(self, by_alias: bool = True):
            return dict(self._data)

    class _SupportedNetworks:
        def __init__(self, value: str):
            self.value = value

        def __str__(self):
            return self.value

    class _FacilitatorClient:
        def __init__(self, *args, **kwargs):
            pass

        async def verify_payment(self, *args, **kwargs):
            return None

        async def settle_payment(self, *args, **kwargs):
            return None

    class _FacilitatorConfig:
        def __init__(self, *args, **kwargs):
            self._data = kwargs

    # Create modules
    x402_mod = ModuleType("x402")
    x402_common = ModuleType("x402.common")
    x402_types = ModuleType("x402.types")
    x402_fac = ModuleType("x402.facilitator")
    x402_encoding = ModuleType("x402.encoding")
    x402_paywall = ModuleType("x402.paywall")

    # Setup x402.common
    x402_common.process_price_to_atomic_amount = lambda price, network: (1, "0x00", {})  # type: ignore[attr-defined]
    x402_common.x402_VERSION = "1.0.0"  # type: ignore[attr-defined]
    x402_common.find_matching_payment_requirements = lambda *args, **kwargs: None  # type: ignore[attr-defined]

    # Setup x402.types
    x402_types.PaymentRequirements = _PaymentRequirements  # type: ignore[attr-defined]
    x402_types.PaymentPayload = _PaymentPayload  # type: ignore[attr-defined]
    x402_types.Price = object  # type: ignore[attr-defined]
    x402_types.SupportedNetworks = _SupportedNetworks  # type: ignore[attr-defined]
    x402_types.PaywallConfig = dict  # type: ignore[attr-defined]
    x402_types.x402PaymentRequiredResponse = _x402PaymentRequiredResponse  # type: ignore[attr-defined]

    # Setup x402.facilitator
    x402_fac.FacilitatorClient = _FacilitatorClient  # type: ignore[attr-defined]
    x402_fac.FacilitatorConfig = _FacilitatorConfig  # type: ignore[attr-defined]

    # Setup x402.encoding
    x402_encoding.safe_base64_decode = lambda x: x.encode() if isinstance(x, str) else x  # type: ignore[attr-defined]

    # Setup x402.paywall
    x402_paywall.get_paywall_html = lambda *args, **kwargs: "<html>Mock Paywall</html>"  # type: ignore[attr-defined]

    # Register all x402 modules
    sys.modules["x402"] = x402_mod
    sys.modules["x402.common"] = x402_common
    sys.modules["x402.types"] = x402_types
    sys.modules["x402.facilitator"] = x402_fac
    sys.modules["x402.encoding"] = x402_encoding
    sys.modules["x402.paywall"] = x402_paywall
