"""Source packager tests."""
from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from bindu.runtime.source_packager import find_project_root


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
