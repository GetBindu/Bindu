"""Tests for RuntimeHandle, RuntimeProvider ABC, and provider registry."""

import pytest

from bindu.runtime.base import (
    RuntimeHandle,
    RuntimeProvider,
    UnknownProviderError,
    _registry,
    get_provider,
    register_provider,
)


def test_runtime_handle_fields():
    h = RuntimeHandle(
        name="x",
        url="http://localhost:3773",
        provider="in-process",
        metadata={},
    )
    assert h.name == "x"
    assert h.url == "http://localhost:3773"
    assert h.provider == "in-process"
    assert h.metadata == {}


def test_runtime_handle_metadata_defaults_to_empty_dict():
    h = RuntimeHandle(name="x", url="http://x", provider="boxd")
    assert h.metadata == {}


def test_abc_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        RuntimeProvider()


def test_register_and_get_provider():
    class FakeProvider(RuntimeProvider):
        async def deploy(self, *a, **kw): ...

        async def health(self, *a, **kw): ...

        async def stream_logs(self, *a, **kw):
            yield b""

        async def on_exit(self, *a, **kw): ...

    register_provider("fake", FakeProvider)
    try:
        p = get_provider("fake")
        assert isinstance(p, FakeProvider)
    finally:
        _registry.pop("fake", None)


def test_unknown_provider_raises():
    with pytest.raises(UnknownProviderError, match="absolutely-not-a-provider"):
        get_provider("absolutely-not-a-provider")
