"""Unit tests for README translation consistency checks."""

from pathlib import Path

from bindu.utils.readme_consistency import (
    check_translated_readme_api_key_prerequisite,
    has_api_key_prerequisite,
    missing_api_key_prerequisite_files,
)


def test_has_api_key_prerequisite_requires_both_variables() -> None:
    """Check that both API key variables are required for consistency pass."""
    text = "OPENROUTER_API_KEY and OPENAI_API_KEY"
    assert has_api_key_prerequisite(text) is True


def test_has_api_key_prerequisite_fails_when_only_one_variable_present() -> None:
    """Check that single-variable mention is reported as missing."""
    text = "Please set OPENROUTER_API_KEY before starting"
    assert has_api_key_prerequisite(text) is False


def test_check_translated_readme_api_key_prerequisite_returns_expected_results(
    tmp_path: Path,
) -> None:
    """Validate checker output across multiple translated README files."""
    (tmp_path / "README.fr.md").write_text(
        "Configure OPENROUTER_API_KEY or OPENAI_API_KEY in env.",
        encoding="utf-8",
    )
    (tmp_path / "README.es.md").write_text(
        "Solo OPENROUTER_API_KEY aquí.",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("Primary README", encoding="utf-8")

    results = check_translated_readme_api_key_prerequisite(tmp_path)

    assert len(results) == 2
    by_name = {result.file_path.name: result for result in results}
    assert by_name["README.fr.md"].has_api_key_prerequisite is True
    assert by_name["README.es.md"].has_api_key_prerequisite is False


def test_missing_api_key_prerequisite_files_lists_only_missing_files(
    tmp_path: Path,
) -> None:
    """Ensure helper returns only the files missing required prerequisite text."""
    passing = tmp_path / "README.de.md"
    failing = tmp_path / "README.ta.md"
    passing.write_text("OPENROUTER_API_KEY and OPENAI_API_KEY", encoding="utf-8")
    failing.write_text("No key prerequisite", encoding="utf-8")

    missing = missing_api_key_prerequisite_files(tmp_path)

    assert missing == [failing]
