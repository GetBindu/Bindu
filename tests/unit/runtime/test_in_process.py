"""Tests for InProcessRuntimeProvider — the default no-op runtime."""
import pytest

from bindu.runtime import RuntimeConfig, get_provider
from bindu.runtime.in_process import InProcessRuntimeProvider


@pytest.mark.asyncio
async def test_deploy_returns_handle():
    p = InProcessRuntimeProvider()
    cfg = RuntimeConfig.from_dict(None)
    h = await p.deploy("my-agent", source_dir=None, config=cfg, env=None)
    assert h.name == "my-agent"
    assert h.provider == "in-process"
    assert h.url.startswith("http://")


@pytest.mark.asyncio
async def test_health_always_true():
    p = InProcessRuntimeProvider()
    cfg = RuntimeConfig.from_dict(None)
    h = await p.deploy("a", None, cfg, None)
    assert await p.health(h) is True


@pytest.mark.asyncio
async def test_on_exit_is_noop():
    p = InProcessRuntimeProvider()
    cfg = RuntimeConfig.from_dict(None)
    h = await p.deploy("a", None, cfg, None)
    await p.on_exit(h, "suspend")
    await p.on_exit(h, "destroy")
    await p.on_exit(h, "detach")


@pytest.mark.asyncio
async def test_stream_logs_yields_nothing():
    p = InProcessRuntimeProvider()
    cfg = RuntimeConfig.from_dict(None)
    h = await p.deploy("a", None, cfg, None)
    chunks = [chunk async for chunk in p.stream_logs(h)]
    assert chunks == []


def test_provider_registered_on_import():
    p = get_provider("in-process")
    assert isinstance(p, InProcessRuntimeProvider)
