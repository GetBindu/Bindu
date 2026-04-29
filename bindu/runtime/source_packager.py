"""Source packaging for runtime providers.

Three concerns:

- ``find_project_root(script_path)``: walks up from the user's entry script to
  find a project-root marker (``pyproject.toml``, ``setup.py``,
  ``requirements.txt``, ``.git``).
- ``should_include(path, root, spec)``: applies default ignores plus
  ``.gitignore`` and ``.binduignore`` patterns loaded into an ``IgnoreSpec``.
- ``build_tarball(root)``: returns gzipped tar bytes of the project tree.
"""

from __future__ import annotations

import fnmatch
import io
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


def find_project_root(script_path: Path) -> Path:
    """Walk up from ``script_path`` looking for a project-root marker.

    Falls back to the script's parent directory if nothing matches.
    """
    script_path = Path(script_path).resolve()
    candidate = script_path.parent
    while True:
        for marker in _ROOT_MARKERS:
            if (candidate / marker).exists():
                return candidate
        parent = candidate.parent
        if parent == candidate:
            return script_path.parent
        candidate = parent


@dataclass(frozen=True)
class IgnoreSpec:
    """Combined ``.gitignore`` + ``.binduignore`` patterns."""

    patterns: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def load(cls, root: Path) -> IgnoreSpec:
        lines: list[str] = []
        for filename in (".gitignore", ".binduignore"):
            f = root / filename
            if f.exists():
                lines.extend(
                    line.strip()
                    for line in f.read_text().splitlines()
                    if line.strip() and not line.strip().startswith("#")
                )
        return cls(patterns=tuple(lines))


def should_include(path: Path, root: Path, spec: IgnoreSpec) -> bool:
    """Decide whether ``path`` should be shipped.

    Returns False if any default-ignored directory appears in ``path``'s
    relative parts, or if any pattern in ``spec`` matches.
    """
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


def build_tarball(root: Path) -> bytes:
    """Tar+gzip everything under ``root`` that survives ``should_include``.

    Returns the gzipped tar as bytes. Files are stored with paths relative
    to ``root`` (e.g. ``agent.py``, ``lib/util.py``).

    Raises:
        SourceTooLargeError: when compressed size > ``MAX_TARBALL_BYTES``.
    """
    spec = IgnoreSpec.load(root)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            if not should_include(path, root, spec):
                continue
            arcname = str(path.relative_to(root)).replace("\\", "/")
            tar.add(path, arcname=arcname, recursive=False)
    blob = buf.getvalue()
    if len(blob) > MAX_TARBALL_BYTES:
        raise SourceTooLargeError(
            f"source tarball is {len(blob) / 1024 / 1024:.1f} MB; "
            f"limit is 50 MB. Add large paths to .binduignore."
        )
    return blob
