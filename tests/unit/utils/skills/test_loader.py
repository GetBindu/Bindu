"""Comprehensive tests for skill loader."""

from typing import Any
from unittest.mock import patch

import pytest
import yaml

from bindu.utils.skills.loader import (
    load_skill_from_directory,
    load_skills,
    find_skill_by_id,
    _parse_markdown_frontmatter,
    _build_skill_from_data,
)


class TestLoadSkillFromDirectory:
    """Test loading skills from directories."""

    def test_load_valid_skill(self, tmp_path):
        """Test loading a valid skill from directory."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()

        skill_data = {
            "name": "Test Skill",
            "description": "A test skill",
            "tags": ["test", "example"],
        }

        skill_yaml = skill_dir / "skill.yaml"
        with open(skill_yaml, "w") as f:
            yaml.dump(skill_data, f)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["name"] == "Test Skill"
        assert skill["description"] == "A test skill"
        assert skill["tags"] == ["test", "example"]

    def test_load_skill_with_relative_path(self, tmp_path):
        """Test loading skill with relative path."""
        skill_dir = tmp_path / "skills" / "my_skill"
        skill_dir.mkdir(parents=True)

        skill_data = {
            "name": "Relative Skill",
            "description": "Loaded via relative path",
        }

        skill_yaml = skill_dir / "skill.yaml"
        with open(skill_yaml, "w") as f:
            yaml.dump(skill_data, f)

        # Load with relative path
        skill = load_skill_from_directory("skills/my_skill", tmp_path)

        assert skill["name"] == "Relative Skill"

    def test_load_skill_missing_directory(self, tmp_path):
        """Test loading from non-existent directory raises error."""
        with pytest.raises(FileNotFoundError, match="Skill directory not found"):
            load_skill_from_directory("nonexistent", tmp_path)

    def test_load_skill_missing_yaml_and_md(self, tmp_path):
        """Test loading from directory without skill.yaml or SKILL.md raises error."""
        skill_dir = tmp_path / "empty_skill"
        skill_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="No skill definition found"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        skill_dir = tmp_path / "bad_skill"
        skill_dir.mkdir()

        skill_yaml = skill_dir / "skill.yaml"
        with open(skill_yaml, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_with_defaults(self, tmp_path):
        """Test that missing optional fields get defaults."""
        skill_dir = tmp_path / "minimal_skill"
        skill_dir.mkdir()

        skill_data = {
            "name": "Minimal Skill",
            "description": "Minimal config",
        }

        skill_yaml = skill_dir / "skill.yaml"
        with open(skill_yaml, "w") as f:
            yaml.dump(skill_data, f)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["id"] == "Minimal Skill"  # Defaults to name
        assert skill["tags"] == []
        assert skill["input_modes"] == ["text/plain"]
        assert skill["output_modes"] == ["text/plain"]

    def test_load_skill_with_all_optional_fields(self, tmp_path):
        """Test loading skill with all optional fields."""
        skill_dir = tmp_path / "full_skill"
        skill_dir.mkdir()

        skill_data = {
            "id": "custom-id",
            "name": "Full Skill",
            "description": "Complete skill",
            "tags": ["tag1", "tag2"],
            "input_modes": ["text/plain", "application/json"],
            "output_modes": ["text/plain"],
            "examples": ["Example 1", "Example 2"],
            "capabilities_detail": {"type": "detailed"},
            "requirements": {"packages": ["req1", "req2"]},
            "performance": {"speed": "fast"},
        }

        skill_yaml = skill_dir / "skill.yaml"
        with open(skill_yaml, "w") as f:
            yaml.dump(skill_data, f)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["id"] == "custom-id"
        assert skill["examples"] == ["Example 1", "Example 2"]
        assert skill["capabilities_detail"] == {"type": "detailed"}
        assert skill["requirements"] == {"packages": ["req1", "req2"]}
        assert skill["performance"] == {"speed": "fast"}

    def test_load_skill_stores_documentation(self, tmp_path):
        """Test that skill stores documentation content."""
        skill_dir = tmp_path / "doc_skill"
        skill_dir.mkdir()

        skill_data = {"name": "Doc Skill", "description": "Has docs"}

        skill_yaml = skill_dir / "skill.yaml"
        with open(skill_yaml, "w") as f:
            yaml.dump(skill_data, f)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert "documentation_content" in skill
        assert "name: Doc Skill" in skill["documentation_content"]

    def test_load_skill_stores_raw_yaml_content(self, tmp_path):
        """Test that skill stores the full raw YAML file content."""
        skill_dir = tmp_path / "raw_skill"
        skill_dir.mkdir()

        raw_yaml = "name: Raw Skill\ndescription: Testing raw content\ntags:\n  - raw\n"
        skill_yaml = skill_dir / "skill.yaml"
        skill_yaml.write_text(raw_yaml)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["documentation_content"] == raw_yaml


class TestLoadSkillFromMarkdown:
    """Test loading skills from SKILL.md files."""

    def test_load_skill_from_md_only(self, tmp_path):
        """Test loading a skill when only SKILL.md exists."""
        skill_dir = tmp_path / "md_skill"
        skill_dir.mkdir()

        md_content = """---
name: MD Skill
description: A skill defined in markdown
tags:
  - markdown
  - test
---

# MD Skill

This is the rich documentation body.

## Usage

Use this skill for testing.
"""
        (skill_dir / "SKILL.md").write_text(md_content)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["name"] == "MD Skill"
        assert skill["description"] == "A skill defined in markdown"
        assert skill["tags"] == ["markdown", "test"]
        assert skill["documentation_content"] == md_content
        assert "# MD Skill" in skill["markdown_content"]
        assert "## Usage" in skill["markdown_content"]

    def test_load_skill_md_with_all_frontmatter_fields(self, tmp_path):
        """Test SKILL.md with full frontmatter metadata."""
        skill_dir = tmp_path / "full_md_skill"
        skill_dir.mkdir()

        md_content = """---
id: full-md-skill
name: Full MD Skill
description: Complete metadata in frontmatter
version: "2.0.0"
author: test@example.com
tags:
  - complete
input_modes:
  - text/plain
  - application/json
output_modes:
  - text/plain
examples:
  - "Example query 1"
  - "Example query 2"
---

# Full MD Skill Documentation

Rich documentation here.
"""
        (skill_dir / "SKILL.md").write_text(md_content)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["id"] == "full-md-skill"
        assert skill["name"] == "Full MD Skill"
        assert skill["version"] == "2.0.0"
        assert skill["author"] == "test@example.com"
        assert skill["input_modes"] == ["text/plain", "application/json"]
        assert skill["examples"] == ["Example query 1", "Example query 2"]

    def test_load_skill_md_missing_frontmatter(self, tmp_path):
        """Test SKILL.md without frontmatter raises error."""
        skill_dir = tmp_path / "no_frontmatter"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text("# Just markdown\nNo frontmatter here.")

        with pytest.raises(ValueError, match="must start with YAML frontmatter"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_md_unclosed_frontmatter(self, tmp_path):
        """Test SKILL.md with unclosed frontmatter raises error."""
        skill_dir = tmp_path / "unclosed_fm"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text("---\nname: Test\ndescription: Test\n")

        with pytest.raises(ValueError, match="frontmatter is not closed"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_md_invalid_frontmatter_yaml(self, tmp_path):
        """Test SKILL.md with invalid YAML in frontmatter raises error."""
        skill_dir = tmp_path / "bad_fm"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text("---\ninvalid: yaml: [\n---\n# Body")

        with pytest.raises(ValueError, match="Invalid YAML in SKILL.md frontmatter"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_md_missing_name(self, tmp_path):
        """Test SKILL.md without name in frontmatter raises error."""
        skill_dir = tmp_path / "no_name"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: No name field\n---\n# Body"
        )

        with pytest.raises(KeyError, match="name"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_md_missing_description(self, tmp_path):
        """Test SKILL.md without description in frontmatter raises error."""
        skill_dir = tmp_path / "no_desc"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text("---\nname: No Description\n---\n# Body")

        with pytest.raises(KeyError, match="description"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_md_empty_body(self, tmp_path):
        """Test SKILL.md with frontmatter but empty body."""
        skill_dir = tmp_path / "empty_body"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text(
            "---\nname: Empty Body\ndescription: No markdown body\n---\n"
        )

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["name"] == "Empty Body"
        assert "markdown_content" not in skill

    def test_load_skill_md_frontmatter_not_dict(self, tmp_path):
        """Test SKILL.md with non-dict frontmatter raises error."""
        skill_dir = tmp_path / "list_fm"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text("---\n- item1\n- item2\n---\n# Body")

        with pytest.raises(ValueError, match="must be a YAML mapping"):
            load_skill_from_directory(skill_dir, tmp_path)


class TestLoadSkillYamlAndMdCombined:
    """Test loading skills when both skill.yaml and SKILL.md exist."""

    def test_yaml_primary_md_enriches(self, tmp_path):
        """Test that skill.yaml is primary and SKILL.md adds markdown_content."""
        skill_dir = tmp_path / "combined_skill"
        skill_dir.mkdir()

        # skill.yaml has the metadata
        skill_data = {
            "name": "Combined Skill",
            "description": "From YAML",
            "tags": ["yaml"],
            "version": "1.0.0",
        }
        with open(skill_dir / "skill.yaml", "w") as f:
            yaml.dump(skill_data, f)

        # SKILL.md has rich documentation
        md_content = """---
name: Combined Skill
description: From MD (ignored since yaml takes priority)
---

# Combined Skill

This rich documentation comes from SKILL.md.

## Detailed Usage

Step-by-step instructions here.
"""
        (skill_dir / "SKILL.md").write_text(md_content)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        # Metadata comes from YAML
        assert skill["name"] == "Combined Skill"
        assert skill["description"] == "From YAML"
        assert skill["tags"] == ["yaml"]

        # documentation_content is the raw YAML
        assert "name: Combined Skill" in skill["documentation_content"]

        # markdown_content is the SKILL.md body
        assert "# Combined Skill" in skill["markdown_content"]
        assert "## Detailed Usage" in skill["markdown_content"]

    def test_yaml_primary_md_malformed_gracefully_handled(self, tmp_path):
        """Test that malformed SKILL.md is gracefully skipped when skill.yaml exists."""
        skill_dir = tmp_path / "yaml_with_bad_md"
        skill_dir.mkdir()

        skill_data = {
            "name": "YAML Primary",
            "description": "SKILL.md is broken but that is ok",
        }
        with open(skill_dir / "skill.yaml", "w") as f:
            yaml.dump(skill_data, f)

        # Malformed SKILL.md (no frontmatter)
        (skill_dir / "SKILL.md").write_text("Just plain markdown, no frontmatter.")

        skill = load_skill_from_directory(skill_dir, tmp_path)

        # Should still load from YAML
        assert skill["name"] == "YAML Primary"
        # Should NOT have markdown_content since MD was malformed
        assert "markdown_content" not in skill


class TestLoadSkills:
    """Test loading multiple skills."""

    def test_load_file_based_skills(self, tmp_path):
        """Test loading file-based skills."""
        # Create two skill directories
        skill1_dir = tmp_path / "skill1"
        skill1_dir.mkdir()
        with open(skill1_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "Skill 1", "description": "First skill"}, f)

        skill2_dir = tmp_path / "skill2"
        skill2_dir.mkdir()
        with open(skill2_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "Skill 2", "description": "Second skill"}, f)

        skills = load_skills(["skill1", "skill2"], tmp_path)

        assert len(skills) == 2
        assert skills[0]["name"] == "Skill 1"
        assert skills[1]["name"] == "Skill 2"

    def test_load_inline_skills(self, tmp_path):
        """Test loading inline skill definitions."""
        inline_skills: list[dict[str, Any]] = [
            {"name": "Inline 1", "description": "First inline"},
            {"name": "Inline 2", "description": "Second inline", "tags": ["test"]},
        ]

        skills = load_skills(inline_skills, tmp_path)  # type: ignore[arg-type]

        assert len(skills) == 2
        assert skills[0]["name"] == "Inline 1"
        assert skills[1]["name"] == "Inline 2"
        assert skills[1]["tags"] == ["test"]

    def test_load_mixed_skills(self, tmp_path):
        """Test loading mix of file-based and inline skills."""
        skill_dir = tmp_path / "file_skill"
        skill_dir.mkdir()
        with open(skill_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "File Skill", "description": "From file"}, f)

        skills_config = [
            "file_skill",
            {"name": "Inline Skill", "description": "Inline def"},
        ]

        skills = load_skills(skills_config, tmp_path)

        assert len(skills) == 2
        assert skills[0]["name"] == "File Skill"
        assert skills[1]["name"] == "Inline Skill"

    def test_load_md_based_skills(self, tmp_path):
        """Test loading skills from SKILL.md files via load_skills."""
        skill_dir = tmp_path / "md_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: MD Skill\ndescription: From markdown\n---\n# Docs\n"
        )

        skills = load_skills(["md_skill"], tmp_path)

        assert len(skills) == 1
        assert skills[0]["name"] == "MD Skill"
        assert skills[0]["description"] == "From markdown"

    def test_load_inline_skill_missing_name(self, tmp_path):
        """Test that inline skill without name raises error."""
        inline_skills: list[dict[str, Any]] = [{"description": "No name"}]

        with pytest.raises(ValueError, match="missing required 'name'"):
            load_skills(inline_skills, tmp_path)  # type: ignore[arg-type]

    def test_load_inline_skill_missing_description(self, tmp_path):
        """Test that inline skill without description raises error."""
        inline_skills: list[dict[str, Any]] = [{"name": "No Description"}]

        with pytest.raises(ValueError, match="missing required 'description'"):
            load_skills(inline_skills, tmp_path)  # type: ignore[arg-type]

    def test_load_inline_skill_with_optional_fields(self, tmp_path):
        """Test inline skill with optional fields."""
        inline_skills: list[dict[str, Any]] = [
            {
                "id": "custom-inline",
                "name": "Rich Inline",
                "description": "Full inline",
                "tags": ["inline"],
                "examples": ["ex1"],
            }
        ]

        skills = load_skills(inline_skills, tmp_path)  # type: ignore[arg-type]

        assert skills[0]["id"] == "custom-inline"
        assert skills[0]["examples"] == ["ex1"]

    def test_load_skills_invalid_type_logs_warning(self, tmp_path):
        """Test that invalid skill type logs warning."""
        with patch("bindu.utils.skills.loader.logger") as mock_logger:
            # Invalid type (not str or dict)
            skills_config: Any = [123]

            # Should log warning but not raise
            skills = load_skills(skills_config, tmp_path)  # type: ignore[arg-type]

            assert len(skills) == 0
            mock_logger.warning.assert_called()

    def test_load_skills_file_error_raises(self, tmp_path):
        """Test that file loading errors are raised."""
        with pytest.raises(FileNotFoundError):
            load_skills(["nonexistent_skill"], tmp_path)


class TestParseMarkdownFrontmatter:
    """Test the markdown frontmatter parser directly."""

    def test_basic_frontmatter(self):
        """Test parsing basic frontmatter."""
        content = "---\nname: Test\ndescription: A test\n---\n# Body"
        frontmatter, body = _parse_markdown_frontmatter(content)

        assert frontmatter["name"] == "Test"
        assert frontmatter["description"] == "A test"
        assert body == "# Body"

    def test_frontmatter_with_rich_body(self):
        """Test parsing frontmatter with rich markdown body."""
        content = """---
name: Rich
description: Rich content
---

# Title

Paragraph with **bold** and *italic*.

## Section

- List item 1
- List item 2
"""
        frontmatter, body = _parse_markdown_frontmatter(content)

        assert frontmatter["name"] == "Rich"
        assert "# Title" in body
        assert "## Section" in body
        assert "- List item 1" in body

    def test_frontmatter_with_complex_yaml(self):
        """Test parsing frontmatter with complex YAML structures."""
        content = """---
name: Complex
description: Complex frontmatter
tags:
  - tag1
  - tag2
capabilities_detail:
  search:
    supported: true
---

# Body
"""
        frontmatter, body = _parse_markdown_frontmatter(content)

        assert frontmatter["tags"] == ["tag1", "tag2"]
        assert frontmatter["capabilities_detail"]["search"]["supported"] is True

    def test_no_frontmatter_raises(self):
        """Test that missing frontmatter raises ValueError."""
        with pytest.raises(ValueError, match="must start with YAML frontmatter"):
            _parse_markdown_frontmatter("# Just markdown")

    def test_unclosed_frontmatter_raises(self):
        """Test that unclosed frontmatter raises ValueError."""
        with pytest.raises(ValueError, match="not closed"):
            _parse_markdown_frontmatter("---\nname: Test\n")

    def test_empty_body(self):
        """Test frontmatter with empty body."""
        content = "---\nname: Test\ndescription: Test\n---\n"
        frontmatter, body = _parse_markdown_frontmatter(content)

        assert frontmatter["name"] == "Test"
        assert body == ""


class TestBuildSkillFromData:
    """Test the skill builder helper."""

    def test_minimal_skill(self):
        """Test building skill with minimal data."""
        data = {"name": "Test", "description": "A test skill"}
        skill = _build_skill_from_data(data)

        assert skill["id"] == "Test"
        assert skill["name"] == "Test"
        assert skill["tags"] == []
        assert skill["input_modes"] == ["text/plain"]
        assert skill["output_modes"] == ["text/plain"]

    def test_missing_name_raises(self):
        """Test that missing name raises KeyError."""
        with pytest.raises(KeyError, match="name"):
            _build_skill_from_data({"description": "No name"})

    def test_missing_description_raises(self):
        """Test that missing description raises KeyError."""
        with pytest.raises(KeyError, match="description"):
            _build_skill_from_data({"name": "No desc"})


class TestFindSkillById:
    """Test finding skills by ID."""

    def test_find_skill_by_id(self):
        """Test finding skill by ID."""
        skills = [
            {"id": "skill-1", "name": "Skill 1"},
            {"id": "skill-2", "name": "Skill 2"},
        ]

        skill = find_skill_by_id(skills, "skill-1")

        assert skill is not None
        assert skill["name"] == "Skill 1"

    def test_find_skill_by_name(self):
        """Test finding skill by name."""
        skills = [
            {"id": "skill-1", "name": "Skill One"},
            {"id": "skill-2", "name": "Skill Two"},
        ]

        skill = find_skill_by_id(skills, "Skill Two")

        assert skill is not None
        assert skill["id"] == "skill-2"

    def test_find_skill_not_found(self):
        """Test that non-existent skill returns None."""
        skills = [{"id": "skill-1", "name": "Skill 1"}]

        skill = find_skill_by_id(skills, "nonexistent")

        assert skill is None

    def test_find_skill_empty_list(self):
        """Test finding in empty skill list."""
        skill = find_skill_by_id([], "any-id")

        assert skill is None
