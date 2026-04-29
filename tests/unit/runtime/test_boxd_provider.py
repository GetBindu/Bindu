"""Tests for BoxdRuntimeProvider — all with the boxd SDK mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bindu.runtime import RuntimeConfig
from bindu.runtime.base import RuntimeHandle
from bindu.runtime.boxd_provider import BoxdRuntimeProvider


def _ok_exec_result():
    """Stub ExecResult with exit_code=0."""
    r = MagicMock()
    r.exit_code = 0
    r.success = True
    r.stdout = ""
    r.stderr = ""
    return r


# ── _resolve_vm ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_vm_creates_when_not_found(mock_boxd, fake_box):
    """If no VM with this name exists, create one."""
    from boxd.errors import NotFoundError

    mock_boxd.box.get.side_effect = NotFoundError("not found")
    p = BoxdRuntimeProvider()

    cfg = RuntimeConfig.from_dict({"provider": "boxd"})
    box = await p._resolve_vm(mock_boxd, "my-agent", cfg)

    mock_boxd.box.get.assert_awaited_once_with("my-agent")
    mock_boxd.box.create.assert_awaited_once()
    assert box is fake_box


@pytest.mark.asyncio
async def test_resolve_vm_reuses_when_found(mock_boxd, fake_box):
    """If a VM already exists, reuse it without creating."""
    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})
    box = await p._resolve_vm(mock_boxd, "my-agent", cfg)

    mock_boxd.box.get.assert_awaited_once_with("my-agent")
    mock_boxd.box.create.assert_not_awaited()
    assert box is fake_box


@pytest.mark.asyncio
async def test_resolve_vm_passes_config(mock_boxd, fake_box):
    """vcpu / memory / disk / image / auto_suspend land in the create call."""
    from boxd.errors import NotFoundError

    mock_boxd.box.get.side_effect = NotFoundError("nope")
    p = BoxdRuntimeProvider()

    cfg = RuntimeConfig.from_dict(
        {
            "provider": "boxd",
            "image": "ghcr.io/me/agent:v1",
            "vcpu": 4,
            "memory": "8G",
            "disk": "40G",
            "auto_suspend": 30,
        }
    )
    await p._resolve_vm(mock_boxd, "my-agent", cfg)

    call = mock_boxd.box.create.await_args
    assert call.kwargs.get("name") == "my-agent"
    assert call.kwargs.get("image") == "ghcr.io/me/agent:v1"
    box_config = call.kwargs.get("config")
    assert box_config is not None
    assert box_config.vcpu == 4
    assert box_config.memory == "8G"
    assert box_config.disk == "40G"
    # auto_suspend goes through LifecycleConfig
    assert box_config.lifecycle is not None
    assert box_config.lifecycle.auto_suspend_timeout == 30
    # default proxy must forward to bindu's default port (3773), not boxd's
    # default (8000), or the public URL is unreachable.
    assert box_config.network is not None
    assert box_config.network.proxies is not None
    assert any(p.port == 3773 for p in box_config.network.proxies)


# ── _ship_source ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ship_source_writes_and_extracts(mock_boxd, fake_box, tmp_path):
    (tmp_path / "agent.py").write_text("# hi\n")
    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._ship_source(fake_box, tmp_path)

    fake_box.write_file.assert_awaited_once()
    args = fake_box.write_file.await_args
    payload, dest = args.args[0], args.args[1]
    assert isinstance(payload, bytes)
    assert dest == "/tmp/source.tar.gz"

    # mkdir + tar extract should have been exec'd into the user-writable dir
    exec_calls = fake_box.exec.await_args_list
    assert any(c.args == ("mkdir", "-p", "/home/boxd/app") for c in exec_calls)
    assert any(
        c.args == ("tar", "xzf", "/tmp/source.tar.gz", "-C", "/home/boxd/app")
        for c in exec_calls
    )


# ── _install_deps ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_deps_with_pyproject(mock_boxd, fake_box):
    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._install_deps(fake_box, has_pyproject=True, has_requirements=False)

    exec_calls = fake_box.exec.await_args_list
    # bindu must always be installed (with --break-system-packages for PEP 668)
    assert any(
        c.args == ("pip", "install", "--break-system-packages", "bindu")
        for c in exec_calls
    )
    # And pip install -e . runs in APP_DIR via sh -c
    assert any(
        c.args[0] == "sh" and "pip install --break-system-packages -e ." in c.args[2]
        for c in exec_calls
    )


@pytest.mark.asyncio
async def test_install_deps_with_requirements(mock_boxd, fake_box):
    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._install_deps(fake_box, has_pyproject=False, has_requirements=True)

    exec_calls = fake_box.exec.await_args_list
    assert any(
        c.args
        == (
            "pip",
            "install",
            "--break-system-packages",
            "-r",
            "/home/boxd/app/requirements.txt",
        )
        for c in exec_calls
    )


@pytest.mark.asyncio
async def test_install_deps_pinned_bindu_version(mock_boxd, fake_box):
    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._install_deps(
        fake_box,
        has_pyproject=False,
        has_requirements=False,
        bindu_version="0.2.5",
    )

    exec_calls = fake_box.exec.await_args_list
    assert any(
        c.args == ("pip", "install", "--break-system-packages", "bindu==0.2.5")
        for c in exec_calls
    )


@pytest.mark.asyncio
async def test_install_deps_raises_on_failure(mock_boxd, fake_box):
    """Non-zero exit code from pip install should raise."""
    bad = MagicMock()
    bad.exit_code = 1
    bad.stderr = "boom"
    fake_box.exec.return_value = bad
    p = BoxdRuntimeProvider()

    with pytest.raises(RuntimeError, match="failed"):
        await p._install_deps(fake_box, has_pyproject=False, has_requirements=False)


# ── _start_agent ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_agent_execs_bindu_serve(mock_boxd, fake_box):
    p = BoxdRuntimeProvider()
    fake_box.exec.return_value = _ok_exec_result()

    await p._start_agent(
        fake_box,
        script="my_agent.py",
        env={"FOO": "bar"},
        public_url="https://my-agent.boxd.sh",
    )

    fake_box.exec.assert_awaited()
    cmd_call = fake_box.exec.await_args
    assert cmd_call.args[0] == "sh"
    assert cmd_call.args[1] == "-c"
    cmd_str = cmd_call.args[2]
    assert "python3" in cmd_str
    assert "/home/boxd/app/my_agent.py" in cmd_str
    # env from caller plus the auto-injected BINDU_PUBLIC_URL
    env = cmd_call.kwargs.get("env")
    assert env is not None
    assert env.get("FOO") == "bar"
    assert env.get("BINDU_PUBLIC_URL") == "https://my-agent.boxd.sh"


@pytest.mark.asyncio
async def test_start_agent_raises_on_nonzero_exit(mock_boxd, fake_box):
    bad = MagicMock()
    bad.exit_code = 1
    bad.stderr = "boom"
    fake_box.exec.return_value = bad

    p = BoxdRuntimeProvider()
    with pytest.raises(RuntimeError, match="failed to start"):
        await p._start_agent(fake_box, script="agent.py")


# ── _wait_healthy ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wait_healthy_returns_when_200(monkeypatch):
    """Health check returns once /health responds 200."""
    p = BoxdRuntimeProvider()

    call_count = {"n": 0}

    class _Resp:
        def __init__(self, status: int):
            self.status_code = status

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            call_count["n"] += 1
            if call_count["n"] < 3:
                return _Resp(503)
            return _Resp(200)

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    # Avoid the 1s sleep inside the loop in tests
    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.asyncio.sleep",
        AsyncMock(return_value=None),
    )

    await p._wait_healthy("https://my-agent.boxd.sh", timeout=10.0)
    assert call_count["n"] == 3


@pytest.mark.asyncio
async def test_wait_healthy_times_out(monkeypatch):
    p = BoxdRuntimeProvider()

    class _Resp:
        status_code = 503

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            return _Resp()

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.asyncio.sleep",
        AsyncMock(return_value=None),
    )

    with pytest.raises(TimeoutError, match="health"):
        await p._wait_healthy("https://my-agent.boxd.sh", timeout=0.1)


# ── deploy() integration ───────────────────────────────────────────


@pytest.fixture
def fake_health(monkeypatch):
    """Skip the actual health-check loop in deploy() tests."""

    async def fake(self, url, timeout=60.0):
        return None

    monkeypatch.setattr(BoxdRuntimeProvider, "_wait_healthy", fake)


@pytest.fixture
def boxd_api_key(monkeypatch):
    monkeypatch.setenv("BOXD_API_KEY", "bxk_test")


@pytest.mark.asyncio
async def test_deploy_a2_full_flow(
    mock_boxd, fake_box, tmp_path, fake_health, boxd_api_key
):
    """A2 deploy: source ship + install + start + healthy."""
    (tmp_path / "agent.py").write_text(
        "from bindu.penguin.bindufy import bindufy\nbindufy({}, lambda m: 'hi')\n"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.1.0'\n")
    fake_box.exec.return_value = _ok_exec_result()
    fake_box.name = "my-agent"
    fake_box.url = "https://my-agent.boxd.sh"

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    handle = await p.deploy(
        agent_name="my-agent",
        source_dir=tmp_path,
        config=cfg,
        env={"OPENAI_API_KEY": "sk-test"},
    )

    assert handle.name == "my-agent"
    assert handle.url == "https://my-agent.boxd.sh"
    assert handle.provider == "boxd"
    assert handle.metadata.get("vm_id") == "vm-1"

    fake_box.write_file.assert_awaited_once()
    pip_calls = [
        c for c in fake_box.exec.await_args_list if c.args and c.args[0] == "pip"
    ]
    assert pip_calls, "pip install should have been called"
    serve_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "python3" in c.args[2]
    ]
    assert serve_calls, "agent script should have been started"


@pytest.mark.asyncio
async def test_deploy_a1_skips_source(mock_boxd, fake_box, fake_health, boxd_api_key):
    """A1 deploy: image-based; no source ship, no pip install."""
    from boxd.errors import NotFoundError

    mock_boxd.box.get.side_effect = NotFoundError("nope")
    fake_box.exec.return_value = _ok_exec_result()
    fake_box.name = "my-agent"
    fake_box.url = "https://my-agent.boxd.sh"

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd", "image": "ghcr.io/me/agent:v1"})

    handle = await p.deploy(
        agent_name="my-agent",
        source_dir=None,
        config=cfg,
        env=None,
    )

    assert handle.url == "https://my-agent.boxd.sh"
    fake_box.write_file.assert_not_awaited()
    pip_calls = [
        c for c in fake_box.exec.await_args_list if c.args and c.args[0] == "pip"
    ]
    assert not pip_calls


@pytest.mark.asyncio
async def test_deploy_requires_credentials(monkeypatch):
    """Missing BOXD_API_KEY/BOXD_TOKEN → raise actionable error."""
    monkeypatch.delenv("BOXD_API_KEY", raising=False)
    monkeypatch.delenv("BOXD_TOKEN", raising=False)
    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    with pytest.raises(RuntimeError, match="BOXD_API_KEY"):
        await p.deploy("agent", None, cfg, None)


# ── health / stream_logs / on_exit ────────────────────────────────


@pytest.mark.asyncio
async def test_health_returns_true_when_200(monkeypatch):
    p = BoxdRuntimeProvider()

    class _Resp:
        status_code = 200

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            return _Resp()

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    h = RuntimeHandle("a", "https://a.boxd.sh", "boxd", {})
    assert await p.health(h) is True


@pytest.mark.asyncio
async def test_health_returns_false_when_unreachable(monkeypatch):
    p = BoxdRuntimeProvider()

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    h = RuntimeHandle("a", "https://a.boxd.sh", "boxd", {})
    assert await p.health(h) is False


@pytest.mark.asyncio
async def test_on_exit_destroy(mock_boxd, fake_box, boxd_api_key):
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {"vm_id": "vm-1"})
    await p.on_exit(h, "destroy")
    fake_box.destroy.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_exit_suspend_does_not_destroy(mock_boxd, fake_box, boxd_api_key):
    """suspend mode relies on boxd's auto_suspend_timeout, not an explicit call."""
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    await p.on_exit(h, "suspend")
    fake_box.destroy.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_exit_detach_is_pure_noop(mock_boxd, fake_box, boxd_api_key):
    """detach mode does not even open a connection."""
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    await p.on_exit(h, "detach")
    fake_box.destroy.assert_not_awaited()
    fake_box.suspend.assert_not_awaited()
    mock_boxd.box.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_stream_logs_yields_chunks(mock_boxd, fake_box, boxd_api_key):
    """stream_logs(follow=True) passes through box.stream_logs output."""
    chunks = [b"hello\n", b"world\n"]

    async def fake_gen(follow=False):
        for c in chunks:
            yield c

    fake_box.stream_logs = fake_gen
    mock_boxd.box.get.return_value = fake_box

    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    out = []
    async for chunk in p.stream_logs(h, follow=True):
        out.append(chunk)
    assert out == chunks
