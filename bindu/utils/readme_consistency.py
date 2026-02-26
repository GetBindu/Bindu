"""Utilities for checking consistency across translated README files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

API_KEY_PATTERN = re.compile(r"OPENROUTER_API_KEY|OPENAI_API_KEY")


@dataclass(frozen=True)
class ReadmeCheckResult:
    """Result for a single README consistency check."""

    file_path: Path
    has_api_key_prerequisite: bool


def _root_readme_translation_files(root: Path) -> list[Path]:
    """Return translated root README files (README.xx.md) sorted by name."""
    return sorted(
        file_path
        for file_path in root.glob("README.*.md")
        if file_path.is_file()
    )


def has_api_key_prerequisite(readme_text: str) -> bool:
    """Check whether a README contains API key prerequisite variables."""
    matches = API_KEY_PATTERN.findall(readme_text)
    if not matches:
        return False
    return {"OPENROUTER_API_KEY", "OPENAI_API_KEY"}.issubset(set(matches))


def check_translated_readme_api_key_prerequisite(root: str | Path) -> list[ReadmeCheckResult]:
    """Check API key prerequisite presence for translated root README files."""
    root_path = Path(root)
    results: list[ReadmeCheckResult] = []

    for readme_file in _root_readme_translation_files(root_path):
        content = readme_file.read_text(encoding="utf-8")
        results.append(
            ReadmeCheckResult(
                file_path=readme_file,
                has_api_key_prerequisite=has_api_key_prerequisite(content),
            )
        )

    return results


def missing_api_key_prerequisite_files(root: str | Path) -> list[Path]:
    """Return translated README files missing API key prerequisite mention."""
    return [
        result.file_path
        for result in check_translated_readme_api_key_prerequisite(root)
        if not result.has_api_key_prerequisite
    ]
