"""Skill loader for Claude-style skill bundles.

This module handles loading skills from filesystem directories containing
skill.yaml or SKILL.md files for rich agent advertisement.

Supported formats:
    1. skill.yaml — YAML file with all skill metadata
    2. SKILL.md — Markdown file with YAML frontmatter (name, description, etc.)
       and rich documentation body
    3. Both — If both exist, skill.yaml provides metadata and SKILL.md provides
       rich documentation content

All file contents are read and stored in the Skill object so that skills are
fully self-contained and can be transmitted over the network (e.g. via gRPC)
without needing filesystem access.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Union, cast

from bindu.common.protocol.types import Skill
from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.skill_loader")

# Supported skill file names
SKILL_YAML_FILENAME = "skill.yaml"
SKILL_MD_FILENAME = "SKILL.md"


def _parse_markdown_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown file.

    Expects the format:
        ---
        name: my-skill
        description: A skill description
        ---
        # Markdown body here

    Args:
        content: Raw markdown file content

    Returns:
        Tuple of (frontmatter_dict, markdown_body)

    Raises:
        ValueError: If frontmatter is missing or malformed
    """
    content = content.strip()

    if not content.startswith("---"):
        raise ValueError(
            "SKILL.md must start with YAML frontmatter (---). "
            "Expected format: ---\\nname: ...\\ndescription: ...\\n---"
        )

    # Find the closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        raise ValueError(
            "SKILL.md frontmatter is not closed. "
            "Expected a closing --- after the YAML block."
        )

    frontmatter_str = content[3:end_idx].strip()
    body = content[end_idx + 3 :].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in SKILL.md frontmatter: {e}")

    if not isinstance(frontmatter, dict):
        raise ValueError(
            "SKILL.md frontmatter must be a YAML mapping (key: value pairs)"
        )

    return frontmatter, body


def _build_skill_from_data(
    skill_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a Skill dict from parsed skill data.

    Extracts required fields with defaults and copies optional fields.

    Args:
        skill_data: Parsed skill metadata (from YAML or frontmatter)

    Returns:
        Skill dictionary with required and optional fields

    Raises:
        KeyError: If required fields (name, description) are missing
    """
    if "name" not in skill_data:
        raise KeyError("Skill definition missing required field 'name'")
    if "description" not in skill_data:
        raise KeyError("Skill definition missing required field 'description'")

    skill: Dict[str, Any] = {
        "id": skill_data.get("id", skill_data["name"]),
        "name": skill_data["name"],
        "description": skill_data["description"],
        "tags": skill_data.get("tags", []),
        "input_modes": skill_data.get("input_modes", ["text/plain"]),
        "output_modes": skill_data.get("output_modes", ["text/plain"]),
    }

    # Add all optional fields if present
    optional_fields = [
        "version",
        "author",
        "examples",
        "capabilities_detail",
        "requirements",
        "performance",
        "allowed_tools",
        "documentation",
        "assessment",
    ]

    for field in optional_fields:
        if field in skill_data:
            skill[field] = skill_data[field]

    return skill


def _load_skill_from_yaml(
    yaml_path: Path, skill_dir: Path, caller_dir: Path
) -> Dict[str, Any]:
    """Load skill metadata from a skill.yaml file.

    Args:
        yaml_path: Path to the skill.yaml file
        skill_dir: Path to the skill directory
        caller_dir: Caller directory for relative path computation

    Returns:
        Skill dictionary with metadata and raw YAML content
    """
    try:
        raw_content = yaml_path.read_text(encoding="utf-8")
    except OSError as e:
        raise FileNotFoundError(f"Cannot read {yaml_path}: {e}")

    try:
        skill_data = yaml.safe_load(raw_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {yaml_path}: {e}")

    skill = _build_skill_from_data(skill_data)

    # Store the file path
    try:
        skill["documentation_path"] = str(yaml_path.relative_to(caller_dir.parent))
    except ValueError:
        skill["documentation_path"] = str(yaml_path)

    # Store raw YAML content so the skill is self-contained
    skill["documentation_content"] = raw_content

    return skill


def _load_skill_from_markdown(
    md_path: Path, skill_dir: Path, caller_dir: Path
) -> Dict[str, Any]:
    """Load skill metadata from a SKILL.md file with YAML frontmatter.

    The SKILL.md file must have YAML frontmatter with at least 'name' and
    'description' fields. The markdown body is stored as rich documentation.

    Args:
        md_path: Path to the SKILL.md file
        skill_dir: Path to the skill directory
        caller_dir: Caller directory for relative path computation

    Returns:
        Skill dictionary with metadata and markdown content
    """
    try:
        raw_content = md_path.read_text(encoding="utf-8")
    except OSError as e:
        raise FileNotFoundError(f"Cannot read {md_path}: {e}")

    frontmatter, markdown_body = _parse_markdown_frontmatter(raw_content)

    skill = _build_skill_from_data(frontmatter)

    # Store the file path
    try:
        skill["documentation_path"] = str(md_path.relative_to(caller_dir.parent))
    except ValueError:
        skill["documentation_path"] = str(md_path)

    # Store the full raw markdown (frontmatter + body) as documentation_content
    skill["documentation_content"] = raw_content

    # Store the markdown body separately for rich documentation
    if markdown_body:
        skill["markdown_content"] = markdown_body

    return skill


def load_skill_from_directory(skill_path: Union[str, Path], caller_dir: Path) -> Skill:
    """Load a skill from a directory containing skill.yaml and/or SKILL.md.

    Resolution order:
        1. If skill.yaml exists, use it for metadata
        2. If SKILL.md also exists, merge its markdown body as rich documentation
        3. If only SKILL.md exists, use its frontmatter for metadata and body for docs
        4. If neither exists, raise FileNotFoundError

    All file contents are read and stored in the returned Skill object, making it
    fully self-contained for network transmission.

    Args:
        skill_path: Path to skill directory (relative or absolute)
        caller_dir: Directory of the calling config file for resolving relative paths

    Returns:
        Skill dictionary with all metadata and documentation content

    Raises:
        FileNotFoundError: If skill directory or skill files don't exist
        ValueError: If skill files are malformed
    """
    # Resolve path
    if isinstance(skill_path, str):
        skill_path = Path(skill_path)

    if not skill_path.is_absolute():
        skill_path = caller_dir / skill_path

    skill_path = skill_path.resolve()

    if not skill_path.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_path}")

    yaml_path = skill_path / SKILL_YAML_FILENAME
    md_path = skill_path / SKILL_MD_FILENAME

    has_yaml = yaml_path.exists()
    has_md = md_path.exists()

    if not has_yaml and not has_md:
        raise FileNotFoundError(
            f"No skill definition found in {skill_path}. "
            f"Expected {SKILL_YAML_FILENAME} or {SKILL_MD_FILENAME}"
        )

    if has_yaml:
        # Primary: load from skill.yaml
        skill = _load_skill_from_yaml(yaml_path, skill_path, caller_dir)

        # If SKILL.md also exists, merge its markdown body as rich documentation
        if has_md:
            try:
                md_content = md_path.read_text(encoding="utf-8")
                _, markdown_body = _parse_markdown_frontmatter(md_content)
                if markdown_body:
                    skill["markdown_content"] = markdown_body
                logger.debug(
                    f"Merged SKILL.md documentation for skill '{skill['name']}'"
                )
            except (ValueError, OSError) as e:
                logger.warning(
                    f"Found SKILL.md alongside skill.yaml in {skill_path} "
                    f"but could not parse it: {e}. Using skill.yaml only."
                )
    else:
        # Fallback: load from SKILL.md only
        skill = _load_skill_from_markdown(md_path, skill_path, caller_dir)

    logger.info(
        f"Loaded skill: {skill['name']} v{skill.get('version', 'unknown')} "
        f"from {skill_path} ({'yaml+md' if has_yaml and has_md else 'yaml' if has_yaml else 'md'})"
    )

    return cast(Skill, skill)


def load_skills(
    skills_config: List[Union[str, Dict[str, Any]]], caller_dir: Path
) -> List[Skill]:
    """Load skills from configuration.

    Supports:
        1. File-based skills: ["path/to/skill/dir"] — directory with skill.yaml or SKILL.md
        2. Inline skills: [{"name": "...", "description": "..."}]
        3. Mixed: both file-based and inline in the same list

    Args:
        skills_config: List of skill paths or inline skill dictionaries
        caller_dir: Directory of the calling config file

    Returns:
        List of loaded Skill objects
    """
    skills: List[Skill] = []

    for skill_item in skills_config:
        try:
            if isinstance(skill_item, str):
                # File-based skill: path to a directory containing skill.yaml or SKILL.md
                skill = load_skill_from_directory(skill_item, caller_dir)
                skills.append(skill)
            elif isinstance(skill_item, dict):
                # Inline skill: dict with at minimum "name" and "description" keys.
                if "name" not in skill_item:
                    raise ValueError(
                        f"Inline skill definition missing required 'name': {skill_item}"
                    )
                if "description" not in skill_item:
                    raise ValueError(
                        f"Inline skill definition missing required 'description': {skill_item}"
                    )
                inline_skill: Dict[str, Any] = {
                    "id": skill_item.get("id", skill_item["name"]),
                    "name": skill_item["name"],
                    "description": skill_item["description"],
                    "tags": skill_item.get("tags", []),
                    "input_modes": skill_item.get("input_modes", ["text/plain"]),
                    "output_modes": skill_item.get("output_modes", ["text/plain"]),
                }
                for field in (
                    "version",
                    "author",
                    "examples",
                    "capabilities_detail",
                    "requirements",
                    "performance",
                    "allowed_tools",
                    "documentation",
                    "assessment",
                ):
                    if field in skill_item:
                        inline_skill[field] = skill_item[field]
                logger.info(f"Loaded inline skill: {inline_skill['name']}")
                skills.append(cast(Skill, inline_skill))
            else:
                logger.warning(
                    f"Invalid skill configuration (expected str path or dict): {skill_item}"
                )
        except (FileNotFoundError, ValueError, KeyError) as e:
            logger.error(f"Failed to load skill {skill_item}: {e}")
            raise

    logger.info(f"Loaded {len(skills)} skill(s)")
    return skills


def find_skill_by_id(
    skills: list[Skill] | list[dict[str, Any]], skill_id: str
) -> Skill | dict[str, Any] | None:
    """Find skill by id or name.

    Args:
        skills: List of skill dictionaries or Skill TypedDicts
        skill_id: Skill ID or name to search for

    Returns:
        Skill dictionary if found, None otherwise
    """
    return next(
        (s for s in skills if s.get("id") == skill_id or s.get("name") == skill_id),
        None,
    )
