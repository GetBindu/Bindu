"""Comprehensive tests for skill loader."""

from typing import Any
from unittest.mock import patch

import pytest
import yaml

from bindu.utils.skills.loader import (
    load_skill_from_directory,
    load_skills,
    find_skill_by_id,
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

    def test_load_skill_missing_yaml(self, tmp_path):
        """Test loading from directory without skill.yaml raises error."""
        skill_dir = tmp_path / "empty_skill"
        skill_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="skill.yaml not found"):
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
