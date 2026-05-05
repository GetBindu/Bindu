"""Tests for ``bindu deploy <script> --runtime=...``.

Cover: capture sentinel wired up correctly, flag parsing, --bindu-version=local
and --image variants pass through to RuntimeConfig, --env KEY=VALUE parsing.
The actual provider deploy call is monkey-patched — these tests don't talk
to a real boxd VM.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_agent_script(tmp_path: Path, name: str = "test-agent") -> Path:
    """Write a minimal bindufy() script to ``tmp_path/agent.py``."""
    script = tmp_path / "agent.py"
    script.write_text(
        f"""
from bindu.penguin.bindufy import bindufy
config = {{
    "author": "test@example.com",
    "name": "{name}",
    "deployment": {{"url": "http://localhost:3773"}},
}}
bindufy(config, lambda messages: "hi", run_server=False)
"""
    )
    # pyproject so find_project_root picks tmp_path as the source root
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "0.1.0"\n'
    )
    return script


def _patch_provider_and_run(monkeypatch, args_list, captured_handle=None):
    """Run ``bindu.cli.main()`` with argv = args_list; provider is mocked.

    Returns the deploy kwargs the mock provider received.
    """
    from bindu import cli as cli_mod

    deploy_kwargs: dict = {}

    async def fake_deploy(**kwargs):
        deploy_kwargs.update(kwargs)
        return captured_handle or MagicMock(name="handle", url="https://x.boxd.sh")

    fake_provider = MagicMock()
    fake_provider.deploy = fake_deploy
    fake_provider.on_exit = AsyncMock()

    async def fake_stream_logs(*a, **kw):
        return
        yield  # noqa  # makes this an async generator

    fake_provider.stream_logs = fake_stream_logs

    import bindu.runtime as br

    monkeypatch.setattr(br, "get_provider", lambda name: fake_provider)

    async def fake_supervise(*a, **kw):
        return

    monkeypatch.setattr(cli_mod, "_supervise", fake_supervise)

    monkeypatch.setattr(sys, "argv", args_list)
    cli_mod.main()
    return deploy_kwargs


def test_deploy_captures_name_from_script(monkeypatch, tmp_path):
    """`bindu deploy agent.py --runtime=boxd` reads agent_name from the script."""
    script = _make_agent_script(tmp_path, name="captured-agent")
    deploy_kwargs = _patch_provider_and_run(
        monkeypatch,
        ["bindu", "deploy", str(script), "--runtime=boxd"],
    )
    assert deploy_kwargs["agent_name"] == "captured-agent"
    assert deploy_kwargs["source_dir"] == tmp_path.resolve()


def test_deploy_name_flag_overrides_script(monkeypatch, tmp_path):
    """--name overrides the script's config name (useful for preview envs)."""
    script = _make_agent_script(tmp_path, name="from-script")
    deploy_kwargs = _patch_provider_and_run(
        monkeypatch,
        ["bindu", "deploy", str(script), "--runtime=boxd", "--name=from-cli"],
    )
    assert deploy_kwargs["agent_name"] == "from-cli"


def test_deploy_passes_resource_flags(monkeypatch, tmp_path):
    """--vcpu, --memory, --disk, --auto-suspend, --on-exit reach RuntimeConfig."""
    script = _make_agent_script(tmp_path)
    deploy_kwargs = _patch_provider_and_run(
        monkeypatch,
        [
            "bindu",
            "deploy",
            str(script),
            "--runtime=boxd",
            "--vcpu=4",
            "--memory=8G",
            "--disk=40G",
            "--auto-suspend=120",
            "--on-exit=destroy",
        ],
    )
    cfg = deploy_kwargs["config"]
    assert cfg.vcpu == 4
    assert cfg.memory == "8G"
    assert cfg.disk == "40G"
    assert cfg.auto_suspend == 120
    assert cfg.on_exit == "destroy"


def test_deploy_bindu_version_local(monkeypatch, tmp_path):
    """--bindu-version=local passes through to RuntimeConfig.bindu_version."""
    script = _make_agent_script(tmp_path)
    deploy_kwargs = _patch_provider_and_run(
        monkeypatch,
        [
            "bindu",
            "deploy",
            str(script),
            "--runtime=boxd",
            "--bindu-version=local",
        ],
    )
    assert deploy_kwargs["config"].bindu_version == "local"


def test_deploy_image_a1_mode(monkeypatch, tmp_path):
    """--image triggers A1 mode (image set, no source ship needed)."""
    script = _make_agent_script(tmp_path)
    deploy_kwargs = _patch_provider_and_run(
        monkeypatch,
        [
            "bindu",
            "deploy",
            str(script),
            "--runtime=boxd",
            "--image=ghcr.io/me/agent:v1",
        ],
    )
    assert deploy_kwargs["config"].image == "ghcr.io/me/agent:v1"


def test_deploy_env_flag_repeated(monkeypatch, tmp_path):
    """--env KEY=VALUE is repeatable and packed into RuntimeConfig.env."""
    script = _make_agent_script(tmp_path)
    deploy_kwargs = _patch_provider_and_run(
        monkeypatch,
        [
            "bindu",
            "deploy",
            str(script),
            "--runtime=boxd",
            "--env",
            "OPENAI_API_KEY=sk-x",
            "--env",
            "DEBUG=1",
        ],
    )
    assert deploy_kwargs["config"].env == {"OPENAI_API_KEY": "sk-x", "DEBUG": "1"}


def test_deploy_env_malformed_exits(monkeypatch, tmp_path):
    """--env without `=` exits non-zero with a helpful message."""
    script = _make_agent_script(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bindu",
            "deploy",
            str(script),
            "--runtime=boxd",
            "--env",
            "BAD_NO_EQUALS",
        ],
    )
    from bindu import cli as cli_mod

    with pytest.raises(SystemExit) as excinfo:
        cli_mod.main()
    assert "KEY=VALUE" in str(excinfo.value)


def test_deploy_in_process_runtime_rejected(monkeypatch, tmp_path):
    """`bindu deploy --runtime=in-process` makes no sense; CLI should refuse."""
    script = _make_agent_script(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["bindu", "deploy", str(script), "--runtime=in-process"]
    )
    from bindu import cli as cli_mod

    with pytest.raises(SystemExit) as excinfo:
        cli_mod.main()
    assert "--runtime" in str(excinfo.value)


def test_deploy_script_not_found(monkeypatch, tmp_path):
    """Missing script path exits with a clear error."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["bindu", "deploy", str(tmp_path / "does-not-exist.py"), "--runtime=boxd"],
    )
    from bindu import cli as cli_mod

    with pytest.raises(SystemExit) as excinfo:
        cli_mod.main()
    assert "not found" in str(excinfo.value)


def test_deploy_script_without_bindufy_exits(monkeypatch, tmp_path):
    """A script that never calls bindufy() exits with a clear error."""
    script = tmp_path / "no_bindufy.py"
    script.write_text("print('hello')\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n'
    )
    monkeypatch.setattr(sys, "argv", ["bindu", "deploy", str(script), "--runtime=boxd"])
    from bindu import cli as cli_mod

    with pytest.raises(SystemExit) as excinfo:
        cli_mod.main()
    assert "did not call bindufy" in str(excinfo.value)


def test_deploy_capture_env_unleaked(monkeypatch, tmp_path):
    """BINDU_DEPLOY_CAPTURE must not leak into the parent env after deploy."""
    monkeypatch.delenv("BINDU_DEPLOY_CAPTURE", raising=False)
    script = _make_agent_script(tmp_path)
    _patch_provider_and_run(
        monkeypatch,
        ["bindu", "deploy", str(script), "--runtime=boxd"],
    )
    assert "BINDU_DEPLOY_CAPTURE" not in os.environ


def test_deploy_threads_script_path_to_provider(monkeypatch, tmp_path):
    """The exact script the user typed reaches provider.deploy as a relative path."""
    sub = tmp_path / "agents"
    sub.mkdir()
    script = sub / "echo.py"
    script.write_text(
        """
from bindu.penguin.bindufy import bindufy
config = {"author": "x@y", "name": "echo", "deployment": {"url": "http://localhost:3773"}}
bindufy(config, lambda m: "hi", run_server=False)
"""
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n'
    )
    deploy_kwargs = _patch_provider_and_run(
        monkeypatch,
        ["bindu", "deploy", str(script), "--runtime=boxd"],
    )
    # script is rooted at the project (where pyproject.toml lives), with the
    # relative subdir preserved — VM will run python3 agents/echo.py.
    assert deploy_kwargs["script"] == "agents/echo.py"
    assert deploy_kwargs["source_dir"] == tmp_path.resolve()


def test_dry_run_skips_provider_call(monkeypatch, tmp_path, capsys):
    """--dry-run prints a plan and never calls provider.deploy."""
    script = _make_agent_script(tmp_path, name="dryagent")

    from bindu import cli as cli_mod

    deploy_called = {"yes": False}

    async def fake_deploy(**kwargs):
        deploy_called["yes"] = True

    fake_provider = MagicMock()
    fake_provider.deploy = fake_deploy
    import bindu.runtime as br

    monkeypatch.setattr(br, "get_provider", lambda name: fake_provider)
    monkeypatch.setattr(
        sys, "argv", ["bindu", "deploy", str(script), "--runtime=boxd", "--dry-run"]
    )
    cli_mod.main()
    out = capsys.readouterr().out

    assert deploy_called["yes"] is False
    assert "DRY RUN" in out
    assert "dryagent" in out
    assert "agent.py" in out
    assert "boxd" in out


def test_dry_run_warns_about_sensitive_files(monkeypatch, tmp_path, capsys):
    """A dropped .env / *.pem is reported with relative path + injection hint."""
    script = _make_agent_script(tmp_path, name="leaky")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-leak\n")
    (tmp_path / "server.pem").write_text("-----BEGIN PRIVATE KEY-----\n")

    from bindu import cli as cli_mod

    fake_provider = MagicMock()

    async def never(**kwargs):
        raise AssertionError("provider.deploy should not be called in dry-run")

    fake_provider.deploy = never
    import bindu.runtime as br

    monkeypatch.setattr(br, "get_provider", lambda name: fake_provider)
    monkeypatch.setattr(
        sys, "argv", ["bindu", "deploy", str(script), "--runtime=boxd", "--dry-run"]
    )
    cli_mod.main()
    out = capsys.readouterr().out

    assert ".env" in out
    assert "server.pem" in out
    assert "--env" in out  # injection hint


def test_warns_on_real_deploy_when_secrets_present(monkeypatch, tmp_path, capsys):
    """Even in non-dry-run mode, emit a stderr warning if secrets were dropped."""
    script = _make_agent_script(tmp_path, name="leaky2")
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-leak\n")
    _patch_provider_and_run(
        monkeypatch,
        ["bindu", "deploy", str(script), "--runtime=boxd"],
    )
    err = capsys.readouterr().err
    assert "sensitive" in err
    assert "--env" in err


def test_capture_sentinel_format(monkeypatch, tmp_path):
    """The JSON dumped by bindufy() in capture mode has the expected shape."""
    from bindu.cli import _capture_agent_metadata

    script = _make_agent_script(tmp_path, name="capture-shape")
    captured = _capture_agent_metadata(str(script))
    assert captured["agent_name"] == "capture-shape"
    # caller_dir is a string path (json-serializable). Resolved against script dir.
    assert Path(captured["caller_dir"]).resolve() == tmp_path.resolve()
