"""Source packager tests."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from bindu.runtime.source_packager import (
    IgnoreSpec,
    SourceTooLargeError,
    build_tarball,
    find_project_root,
    should_include,
)


# ── Project-root discovery ─────────────────────────────────────────


def test_finds_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    sub = tmp_path / "src" / "deep"
    sub.mkdir(parents=True)
    script = sub / "agent.py"
    script.write_text("# agent")
    assert find_project_root(script) == tmp_path


def test_finds_setup_py(tmp_path: Path):
    (tmp_path / "setup.py").write_text("from setuptools import setup\n")
    script = tmp_path / "agent.py"
    script.write_text("# agent")
    assert find_project_root(script) == tmp_path


def test_finds_requirements_txt(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("httpx\n")
    script = tmp_path / "agent.py"
    script.write_text("# agent")
    assert find_project_root(script) == tmp_path


def test_finds_git(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "sub"
    sub.mkdir()
    script = sub / "agent.py"
    script.write_text("# agent")
    assert find_project_root(script) == tmp_path


def test_falls_back_to_script_dir(tmp_path: Path):
    """No marker found → script's parent is the root."""
    sub = tmp_path / "lonely"
    sub.mkdir()
    script = sub / "agent.py"
    script.write_text("# agent")
    assert find_project_root(script) == sub


def test_marker_priority(tmp_path: Path):
    """pyproject.toml at the same level wins over setup.py."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "setup.py").write_text("from setuptools import setup\n")
    script = tmp_path / "agent.py"
    script.write_text("# agent")
    assert find_project_root(script) == tmp_path


# ── Ignore handling ────────────────────────────────────────────────


def _make_spec(root: Path, gitignore: str = "", binduignore: str = "") -> IgnoreSpec:
    if gitignore:
        (root / ".gitignore").write_text(gitignore)
    if binduignore:
        (root / ".binduignore").write_text(binduignore)
    return IgnoreSpec.load(root)


def test_default_ignores_pycache(tmp_path: Path):
    spec = _make_spec(tmp_path)
    assert not should_include(tmp_path / "x" / "__pycache__" / "y.pyc", tmp_path, spec)


def test_default_ignores_git(tmp_path: Path):
    spec = _make_spec(tmp_path)
    assert not should_include(tmp_path / ".git" / "config", tmp_path, spec)


def test_default_ignores_venv(tmp_path: Path):
    spec = _make_spec(tmp_path)
    assert not should_include(tmp_path / ".venv" / "bin" / "python", tmp_path, spec)
    assert not should_include(tmp_path / "venv" / "bin" / "python", tmp_path, spec)


def test_default_ignores_node_modules(tmp_path: Path):
    spec = _make_spec(tmp_path)
    assert not should_include(
        tmp_path / "node_modules" / "x" / "index.js", tmp_path, spec
    )


def test_default_ignores_pyc_files(tmp_path: Path):
    spec = _make_spec(tmp_path)
    assert not should_include(tmp_path / "module.pyc", tmp_path, spec)


def test_includes_regular_python(tmp_path: Path):
    spec = _make_spec(tmp_path)
    assert should_include(tmp_path / "agent.py", tmp_path, spec)


def test_excludes_dotenv(tmp_path: Path):
    """`.env` is NEVER shipped — secrets must be injected via --env KEY=VAL."""
    spec = _make_spec(tmp_path)
    assert not should_include(tmp_path / ".env", tmp_path, spec)
    assert not should_include(tmp_path / ".env.local", tmp_path, spec)
    assert not should_include(tmp_path / ".env.production", tmp_path, spec)


def test_excludes_pem_and_keys(tmp_path: Path):
    """*.pem, *.key, id_rsa* are never shipped — they're private credentials."""
    spec = _make_spec(tmp_path)
    assert not should_include(tmp_path / "server.pem", tmp_path, spec)
    assert not should_include(tmp_path / "deploy.key", tmp_path, spec)
    assert not should_include(tmp_path / "id_rsa", tmp_path, spec)
    assert not should_include(tmp_path / "id_ed25519", tmp_path, spec)
    assert not should_include(tmp_path / "creds.kdbx", tmp_path, spec)
    assert not should_include(tmp_path / "credentials.json", tmp_path, spec)


def test_excludes_aws_ssh_dirs(tmp_path: Path):
    """Anything under .aws/, .ssh/, .gnupg/, .bindu/ is dropped."""
    spec = _make_spec(tmp_path)
    assert not should_include(tmp_path / ".aws" / "credentials", tmp_path, spec)
    assert not should_include(tmp_path / ".ssh" / "id_rsa", tmp_path, spec)
    assert not should_include(tmp_path / ".gnupg" / "secring.gpg", tmp_path, spec)
    assert not should_include(tmp_path / ".bindu" / "did" / "agent.pem", tmp_path, spec)


def test_find_sensitive_files(tmp_path: Path):
    """find_sensitive_files reports every secret that exists on disk."""
    from bindu.runtime.source_packager import find_sensitive_files

    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-xxx\n")
    (tmp_path / "server.pem").write_text("-----BEGIN PRIVATE KEY-----\n")
    (tmp_path / ".aws").mkdir()
    (tmp_path / ".aws" / "credentials").write_text("[default]\n")
    (tmp_path / "agent.py").write_text("# fine\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")

    found = {p.name for p in find_sensitive_files(tmp_path)}
    assert ".env" in found
    assert "server.pem" in found
    assert "credentials" in found  # under .aws/
    assert "agent.py" not in found


def test_gitignore_pattern(tmp_path: Path):
    spec = _make_spec(tmp_path, gitignore="*.log\nsecrets/\n")
    assert not should_include(tmp_path / "app.log", tmp_path, spec)
    assert not should_include(tmp_path / "secrets" / "key.pem", tmp_path, spec)
    assert should_include(tmp_path / "agent.py", tmp_path, spec)


def test_binduignore_pattern(tmp_path: Path):
    spec = _make_spec(tmp_path, binduignore="data/\n")
    assert not should_include(tmp_path / "data" / "big.csv", tmp_path, spec)


def test_default_ignore_persists_with_binduignore(tmp_path: Path):
    """A .binduignore file does not turn off the built-in defaults."""
    spec = _make_spec(tmp_path, binduignore="other/\n")
    assert not should_include(tmp_path / "__pycache__" / "x.pyc", tmp_path, spec)


# ── Tarball building ───────────────────────────────────────────────


def test_build_tarball_basic(tmp_path: Path):
    (tmp_path / "agent.py").write_text("print('hi')\n")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    sub = tmp_path / "lib"
    sub.mkdir()
    (sub / "util.py").write_text("# util\n")

    blob = build_tarball(tmp_path)
    assert isinstance(blob, bytes)
    assert len(blob) > 0

    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        names = sorted(tar.getnames())
    assert "agent.py" in names
    assert "pyproject.toml" in names
    assert "lib/util.py" in names


def test_build_tarball_skips_ignored(tmp_path: Path):
    (tmp_path / "agent.py").write_text("# agent\n")
    pcache = tmp_path / "__pycache__"
    pcache.mkdir()
    (pcache / "agent.cpython-312.pyc").write_bytes(b"\x00" * 100)
    (tmp_path / ".gitignore").write_text("secrets/\n")
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "key.pem").write_text("hush")

    blob = build_tarball(tmp_path)

    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        names = sorted(tar.getnames())
    assert "agent.py" in names
    assert not any(n.startswith("__pycache__") for n in names)
    assert not any(n.startswith("secrets") for n in names)


def test_build_tarball_size_cap(tmp_path: Path):
    """60 MB of incompressible data exceeds the 50 MB cap."""
    import os

    big = tmp_path / "huge.bin"
    big.write_bytes(os.urandom(60 * 1024 * 1024))

    with pytest.raises(SourceTooLargeError, match="50 MB"):
        build_tarball(tmp_path)
