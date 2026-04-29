"""Source packaging for runtime providers.

- ``find_project_root(start_dir)``: walks up looking for a project-root marker.
- ``IgnoreSpec`` + ``should_include``: default ignores plus ``.gitignore`` and
  ``.binduignore``.
- ``build_tarball(root)``: returns gzipped tar bytes of the project tree.
"""

from __future__ import annotations

import fnmatch
import io
import os
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

# Order = priority. First match wins.
_ROOT_MARKERS = ("pyproject.toml", "setup.py", "requirements.txt", ".git")

# Always-applied excludes. Match any directory segment.
_DEFAULT_IGNORE_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
)
_DEFAULT_IGNORE_SUFFIXES = (".pyc", ".pyo", ".log", ".sqlite", ".db")

MAX_TARBALL_BYTES = 50 * 1024 * 1024  # 50 MB compressed


def find_project_root(start_dir: Path) -> Path:
    """Walk up from ``start_dir`` looking for a project-root marker.

    Falls back to ``start_dir`` itself if nothing matches.
    """
    start_dir = Path(start_dir).resolve()
    candidate = start_dir if start_dir.is_dir() else start_dir.parent
    fallback = candidate
    while True:
        for marker in _ROOT_MARKERS:
            if (candidate / marker).exists():
                return candidate
        parent = candidate.parent
        if parent == candidate:
            return fallback
        candidate = parent


def _read_pattern_file(path: Path) -> list[str]:
    try:
        text = path.read_text()
    except FileNotFoundError:
        return []
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


@dataclass(frozen=True)
class IgnoreSpec:
    """Combined ``.gitignore`` + ``.binduignore`` patterns."""

    patterns: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def load(cls, root: Path) -> IgnoreSpec:
        """Load patterns from ``.gitignore`` and ``.binduignore`` at ``root``."""
        lines: list[str] = []
        for filename in (".gitignore", ".binduignore"):
            lines.extend(_read_pattern_file(root / filename))
        return cls(patterns=tuple(lines))


def should_include(path: Path, root: Path, spec: IgnoreSpec) -> bool:
    """Decide whether ``path`` should be shipped."""
    rel = path.relative_to(root)
    parts = rel.parts

    if any(p in _DEFAULT_IGNORE_DIRS for p in parts):
        return False

    if path.suffix in _DEFAULT_IGNORE_SUFFIXES:
        return False

    rel_str = str(rel).replace("\\", "/")
    for pat in spec.patterns:
        if pat.endswith("/"):
            dir_pat = pat.rstrip("/")
            if rel_str == dir_pat or rel_str.startswith(dir_pat + "/"):
                return False
        elif fnmatch.fnmatch(rel_str, pat) or fnmatch.fnmatch(rel.name, pat):
            return False

    return True


class SourceTooLargeError(Exception):
    """Raised when the project source exceeds the tarball size cap."""


def _walk_included(root: Path, spec: IgnoreSpec) -> list[Path]:
    """Yield files under ``root`` that pass ``should_include``.

    Uses ``os.walk`` with in-place pruning of default-ignored directories
    so we never descend into ``.venv`` / ``node_modules`` / etc.
    """
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune default-ignored directories before descending.
        dirnames[:] = [d for d in dirnames if d not in _DEFAULT_IGNORE_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if should_include(p, root, spec):
                files.append(p)
    files.sort()
    return files


def build_tarball(root: Path) -> bytes:
    """Tar+gzip everything under ``root`` that survives ``should_include``.

    Returns the gzipped tar as bytes. Files are stored with paths relative
    to ``root``.

    Raises:
        SourceTooLargeError: when compressed size > ``MAX_TARBALL_BYTES``.
    """
    spec = IgnoreSpec.load(root)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in _walk_included(root, spec):
            arcname = str(path.relative_to(root)).replace("\\", "/")
            tar.add(path, arcname=arcname, recursive=False)
    blob = buf.getvalue()
    if len(blob) > MAX_TARBALL_BYTES:
        raise SourceTooLargeError(
            f"source tarball is {len(blob) / 1024 / 1024:.1f} MB; "
            f"limit is 50 MB. Add large paths to .binduignore."
        )
    return blob
