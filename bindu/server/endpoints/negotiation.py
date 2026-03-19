# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Negotiation endpoint for capability assessment.

This endpoint evaluates how well the agent can handle a task
based on skills, performance, load, and pricing constraints.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.server.applications import BinduApplication
from bindu.server.negotiation.capability_calculator import (
    CapabilityCalculator,
    ScoringWeights,
)
from .utils import (
    create_response_with_x402,
    handle_endpoint_errors,
    get_client_ip,
    validate_authentication,
    validate_manifest,
)
from bindu.utils.logging import get_logger
from bindu.utils.capabilities import get_x402_extension_from_capabilities
from bindu.settings import app_settings

logger = get_logger("bindu.server.endpoints.negotiation")

# Constants
MAX_TASK_SUMMARY_LENGTH = 10000
DEFAULT_MIN_SCORE = 0.0
DEFAULT_SCORING_WEIGHTS = {
    "skill_match": 0.55,
    "io_compatibility": 0.20,
    "performance": 0.15,
    "load": 0.05,
    "cost": 0.05,
}


def _build_negotiation_response(result: Any) -> dict:
    """Build negotiation response from calculation result.

    Args:
        result: CapabilityCalculator result

    Returns:
        Response data dict with optional fields included conditionally
    """
    response = {
        "accepted": result.accepted,
        "score": result.score,
        "confidence": result.confidence,
    }

    # Add optional fields if present
    if result.rejection_reason:
        response["rejection_reason"] = result.rejection_reason

    if result.skill_matches:
        response["skill_matches"] = [
            {
                "skill_id": m.skill_id,
                "skill_name": m.skill_name,
                "score": m.score,
                "reasons": m.reasons,
            }
            for m in result.skill_matches
        ]

    if result.matched_tags:
        response["matched_tags"] = result.matched_tags

    if result.matched_capabilities:
        response["matched_capabilities"] = result.matched_capabilities

    if result.latency_estimate_ms is not None:
        response["latency_estimate_ms"] = result.latency_estimate_ms

    if result.queue_depth is not None:
        response["queue_depth"] = result.queue_depth

    if result.subscores:
        response["subscores"] = result.subscores

    return response


def _get_or_create_calculator(app: BinduApplication) -> CapabilityCalculator:
    """Get or create cached calculator instance.

    Caches calculator in app instance to avoid repeated initialization.
    Invalidates cache if manifest changes.
    """
    # Check if calculator exists and manifest hasn't changed
    if (
        hasattr(app, "_negotiation_calculator")
        and hasattr(app, "_negotiation_calculator_manifest_id")
        and app._negotiation_calculator_manifest_id == id(app.manifest)
    ):
        return app._negotiation_calculator  # type: ignore[return-value]

    # Create new calculator
    skills = app.manifest.skills or [] if app.manifest else []
    x402_extension = (
        get_x402_extension_from_capabilities(app.manifest) if app.manifest else None
    )

    # Get embedding API key from manifest negotiation config if available
    embedding_api_key = None
    if (
        app.manifest
        and hasattr(app.manifest, "negotiation")
        and app.manifest.negotiation
    ):
        embedding_api_key = app.manifest.negotiation.get("embedding_api_key")

    calculator = CapabilityCalculator(
        skills=skills,
        x402_extension=x402_extension,
        embedding_api_key=embedding_api_key,
    )

    # Cache calculator and manifest ID
    app._negotiation_calculator = calculator  # type: ignore[attr-defined]
    app._negotiation_calculator_manifest_id = id(app.manifest)  # type: ignore[attr-defined]

    logger.debug("Created and cached new CapabilityCalculator instance")
    return calculator


@handle_endpoint_errors("task assessment")
async def negotiation_endpoint(app: BinduApplication, request: Request) -> Response:
    """Assess agent's capability to handle a task.

    Evaluates skill match, IO compatibility, performance, load, and cost
    to produce an acceptance decision with confidence and detailed scoring.
    """
    client_ip = get_client_ip(request)
    logger.debug(f"Negotiation request from {client_ip}")

    # Authentication guard (protect negotiation when enabled)
    auth_error = validate_authentication(request, client_ip, "negotiation")
    if auth_error:
        return auth_error

    # Early validation: manifest exists
    error_resp = validate_manifest(app)
    if error_resp:
        return error_resp

    # Early validation: parse request body
    try:
        body = await request.json()
    except Exception as e:
        logger.warning(f"Invalid JSON in negotiation request: {e}")
        return JSONResponse(content={"error": "Invalid JSON payload"}, status_code=400)

    # Early validation: required field
    task_summary = body.get("task_summary")
    if not task_summary:
        return JSONResponse(
            content={"error": "'task_summary' is required"}, status_code=400
        )

    # Early validation: task_summary length
    if len(task_summary) > MAX_TASK_SUMMARY_LENGTH:
        return JSONResponse(
            content={
                "error": f"task_summary exceeds maximum length of {MAX_TASK_SUMMARY_LENGTH} characters"
            },
            status_code=400,
        )

    # Extract optional fields
    task_details = body.get("task_details")
    input_mime_types = body.get("input_mime_types")
    output_mime_types = body.get("output_mime_types")
    max_latency_ms = body.get("max_latency_ms")
    max_cost_amount = body.get("max_cost_amount")

    required_tools = body.get("required_tools")
    forbidden_tools = body.get("forbidden_tools")
    min_score = body.get("min_score", DEFAULT_MIN_SCORE)

    # Extract custom weights if provided
    weights = None
    if "weights" in body:
        w = body["weights"]
        try:
            weights = ScoringWeights(
                skill_match=w.get(
                    "skill_match", DEFAULT_SCORING_WEIGHTS["skill_match"]
                ),
                io_compatibility=w.get(
                    "io_compatibility", DEFAULT_SCORING_WEIGHTS["io_compatibility"]
                ),
                performance=w.get(
                    "performance", DEFAULT_SCORING_WEIGHTS["performance"]
                ),
                load=w.get("load", DEFAULT_SCORING_WEIGHTS["load"]),
                cost=w.get("cost", DEFAULT_SCORING_WEIGHTS["cost"]),
            )
        except ValueError as e:
            return JSONResponse(
                content={"error": f"Invalid weights: {e}"}, status_code=400
            )

    # Get queue depth by counting non-terminal tasks from storage
    queue_depth = None
    if app.task_manager and app.task_manager.storage:
        try:
            tasks = await app.task_manager.storage.list_tasks()
            # Count tasks in non-terminal states (from agent settings)
            # Task dicts returned by storage have status nested as
            # task["status"]["state"], not top-level task["state"] — reading
            # the wrong key made queue_depth always 0, so load score was
            # permanently pegged at 1.0 regardless of actual queue depth.
            queue_depth = sum(
                1
                for task in tasks
                if task.get("status", {}).get("state")
                in app_settings.agent.non_terminal_states
            )
        except Exception as e:
            logger.warning(f"Failed to get queue depth from storage: {e}")

    # Get or create cached calculator instance
    calculator = _get_or_create_calculator(app)

    # Run calculation (async — embedder uses httpx.AsyncClient)
    result = await calculator.calculate(
        task_summary=task_summary,
        task_details=task_details,
        input_mime_types=input_mime_types,
        output_mime_types=output_mime_types,
        max_latency_ms=max_latency_ms,
        max_cost_amount=max_cost_amount,
        required_tools=required_tools,
        forbidden_tools=forbidden_tools,
        queue_depth=queue_depth,
        weights=weights,
        min_score=min_score,
    )

    # Build response with optional fields
    response_data = _build_negotiation_response(result)

    logger.info(
        f"Assessment for '{task_summary[:50]}...': "
        f"accepted={result.accepted}, score={result.score}, "
        f"confidence={result.confidence}"
    )

    return create_response_with_x402(request, response_data)
