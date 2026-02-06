"""Skills endpoints for detailed skill documentation and discovery.

These endpoints provide rich skill metadata for orchestrators to make
intelligent agent selection and routing decisions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import InternalError, InvalidParamsError, SkillNotFoundError
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)
from bindu.server.applications import BinduApplication
from bindu.utils.request_utils import handle_endpoint_errors
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error
from bindu.utils.skill_utils import find_skill_by_id

logger = get_logger("bindu.server.endpoints.skills")


class SkillQueryParams(BaseModel):
    """Pydantic model for validating skills list query parameters."""

    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of skills to return")
    offset: int = Field(default=0, ge=0, description="Number of skills to skip")
    tags: str | None = Field(default=None, description="Comma-separated list of tags to filter by")

    @classmethod
    def from_request(cls, request: Request) -> SkillQueryParams:
        """Parse and validate query parameters from request.

        Args:
            request: Starlette request object

        Returns:
            Validated SkillQueryParams instance

        Raises:
            ValidationError: If parameters are invalid
        """
        query_params = request.query_params
        
        # Build dict with defaults, Pydantic will handle validation
        params_dict: dict[str, Any] = {}
        
        if "limit" in query_params:
            params_dict["limit"] = query_params["limit"]
        if "offset" in query_params:
            params_dict["offset"] = query_params["offset"]
        if "tags" in query_params:
            params_dict["tags"] = query_params["tags"]
        
        # Pydantic will validate and convert types automatically
        return cls(**params_dict)


@handle_endpoint_errors("skills list")
async def skills_list_endpoint(app: BinduApplication, request: Request) -> Response:
    """List all skills available on this agent.

    Returns a summary of all skills with basic metadata for discovery.
    Supports query parameters:
    - limit: Maximum number of skills to return (1-1000, default: 100)
    - offset: Number of skills to skip (>=0, default: 0)
    - tags: Comma-separated list of tags to filter by

    Args:
        app: Bindu application instance
        request: Starlette request object

    Returns:
        JSONResponse with skills list and pagination metadata
    """
    client_ip: str = get_client_ip(request)
    logger.debug(f"Serving skills list to {client_ip}")

    # Validate query parameters
    try:
        query_params: SkillQueryParams = SkillQueryParams.from_request(request)
    except ValidationError as e:
        logger.warning(f"Invalid query parameters from {client_ip}: {e}")
        code, message = extract_error_fields(InvalidParamsError)
        return jsonrpc_error(
            code,
            message,
            f"Invalid query parameters: {e.errors()[0]['msg'] if e.errors() else 'Invalid parameters'}",
            status=400,
        )

    # Ensure manifest exists
    if app.manifest is None:
        logger.error(f"Agent manifest not configured (requested by {client_ip})")
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, "Agent manifest not configured", status=500)

    # Get skills from manifest
    skills: list[dict[str, Any]] = app.manifest.skills or []

    # Filter by tags if provided
    filtered_skills: list[dict[str, Any]] = skills
    if query_params.tags:
        tag_list: list[str] = [tag.strip() for tag in query_params.tags.split(",") if tag.strip()]
        if tag_list:
            filtered_skills = [
                skill
                for skill in skills
                if any(tag in skill.get("tags", []) for tag in tag_list)
            ]

    # Build summary response
    skills_summary: list[dict[str, Any]] = []
    for skill in filtered_skills:
        skill_item: dict[str, Any] = {
            "id": skill.get("id"),
            "name": skill.get("name"),
            "description": skill.get("description"),
            "version": skill.get("version", "unknown"),
            "tags": skill.get("tags", []),
            "input_modes": skill.get("input_modes", []),
            "output_modes": skill.get("output_modes", []),
        }

        # Add optional fields if present
        if "examples" in skill:
            skill_item["examples"] = skill["examples"]

        if "documentation_path" in skill:
            skill_item["documentation_path"] = skill["documentation_path"]

        skills_summary.append(skill_item)

    # Apply pagination
    total_count: int = len(skills_summary)
    paginated_skills: list[dict[str, Any]] = skills_summary[
        query_params.offset : query_params.offset + query_params.limit
    ]

    # Build response with pagination metadata
    response_data: dict[str, Any] = {
        "skills": paginated_skills,
        "total": total_count,
        "limit": query_params.limit,
        "offset": query_params.offset,
        "has_more": query_params.offset + query_params.limit < total_count,
    }

    resp: JSONResponse = JSONResponse(content=response_data)
    if x402_is_requested(request):
        resp = x402_add_header(resp)
    return resp


@handle_endpoint_errors("skill detail")
async def skill_detail_endpoint(app: BinduApplication, request: Request) -> Response:
    """Get detailed information about a specific skill.

    Returns full skill metadata including documentation, capabilities,
    requirements, and performance characteristics.

    Args:
        app: Bindu application instance
        request: Starlette request object

    Returns:
        JSONResponse with full skill detail
    """
    client_ip: str = get_client_ip(request)
    skill_id: str | None = request.path_params.get("skill_id")

    if not skill_id:
        logger.warning(f"Skill ID not provided (requested by {client_ip})")
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, message, "Skill ID not provided", status=404)

    logger.debug(f"Serving skill detail for '{skill_id}' to {client_ip}")

    # Ensure manifest exists
    if app.manifest is None:
        logger.error(f"Agent manifest not configured (requested by {client_ip})")
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, "Agent manifest not configured", status=500)

    # Find skill in manifest
    skills: list[dict[str, Any]] = app.manifest.skills or []
    skill: dict[str, Any] | None = find_skill_by_id(skills, skill_id)

    if not skill:
        logger.warning(f"Skill not found: {skill_id} (requested by {client_ip})")
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, message, f"Skill not found: {skill_id}", status=404)

    # Return full skill data (excluding documentation_content for size)
    skill_detail: dict[str, Any] = dict(skill)

    # Remove documentation_content from response (too large)
    # Clients should use /agent/skills/{skill_id}/documentation for that
    if "documentation_content" in skill_detail:
        skill_detail["has_documentation"] = True
        del skill_detail["documentation_content"]
    else:
        skill_detail["has_documentation"] = False

    resp: JSONResponse = JSONResponse(content=skill_detail)
    if x402_is_requested(request):
        resp = x402_add_header(resp)
    return resp


@handle_endpoint_errors("skill documentation")
async def skill_documentation_endpoint(
    app: BinduApplication, request: Request
) -> Response:
    """Get the full skill.yaml documentation for a specific skill.

    Returns the complete YAML documentation that orchestrators can use
    to understand when and how to use this skill.

    Args:
        app: Bindu application instance
        request: Starlette request object

    Returns:
        Response with YAML documentation content
    """
    client_ip: str = get_client_ip(request)
    skill_id: str | None = request.path_params.get("skill_id")

    if not skill_id:
        logger.warning(f"Skill ID not provided (requested by {client_ip})")
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, message, "Skill ID not provided", status=404)

    logger.debug(f"Serving skill documentation for '{skill_id}' to {client_ip}")

    # Ensure manifest exists
    if app.manifest is None:
        logger.error(f"Agent manifest not configured (requested by {client_ip})")
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, "Agent manifest not configured", status=500)

    # Find skill in manifest
    skills: list[dict[str, Any]] = app.manifest.skills or []
    skill: dict[str, Any] | None = find_skill_by_id(skills, skill_id)

    if not skill:
        logger.warning(f"Skill not found: {skill_id} (requested by {client_ip})")
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, message, f"Skill not found: {skill_id}", status=404)

    # Get documentation content
    documentation: str | None = skill.get("documentation_content")

    if not documentation:
        logger.warning(f"No documentation available for skill: {skill_id} (requested by {client_ip})")
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(
            code, message, f"No documentation available for skill: {skill_id}", status=404
        )

    # Return as YAML
    resp: Response = Response(content=documentation, media_type="application/yaml")
    if x402_is_requested(request):
        resp = x402_add_header(resp)
    return resp
