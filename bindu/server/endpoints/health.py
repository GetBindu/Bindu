"""Health check endpoint for service monitoring."""

from __future__ import annotations

from time import monotonic

from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu import __version__
from bindu.server.applications import BinduApplication
from .utils import handle_endpoint_errors, get_agent_did, get_runtime_status
from bindu.utils.logging import get_logger

import os
import platform
import sys


logger = get_logger("bindu.server.endpoints.health")

_start_time = monotonic()


def _build_health_payload(
    app: BinduApplication,
    runtime: dict,
    agent_did: str | None,
) -> dict:
    """Build common health check payload.

    Args:
        app: BinduApplication instance
        runtime: Runtime status dict from get_runtime_status()
        agent_did: Agent DID if available

    Returns:
        Health payload dict with common fields
    """
    return {
        "version": __version__,
        "health": "healthy" if runtime["strict_ready"] else "degraded",
        "runtime": {
            "storage_backend": runtime["storage_type"],
            "scheduler_backend": runtime["scheduler_type"],
            "task_manager_running": runtime["task_manager_running"],
            "strict_ready": runtime["strict_ready"],
        },
        "application": {
            "penguin_id": str(app.penguin_id),
            "agent_did": agent_did,
        },
        "system": {
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "platform_release": platform.release(),
            "environment": os.getenv("ENV", "development"),
        },
    }


@handle_endpoint_errors("health check")
async def health_endpoint(app: BinduApplication, request: Request) -> JSONResponse:
    """Health check endpoint with strict readiness validation.

    Returns HTTP 200 when all components (storage, scheduler, task-manager) are running.
    Returns HTTP 503 when any component is not ready.

    This endpoint is suitable for Kubernetes readiness/liveness probes and general
    health monitoring.
    """
    # Get runtime status
    runtime = get_runtime_status(app)

    # Get agent DID if available
    agent_did = get_agent_did(app)

    # Build payload with common fields
    payload = _build_health_payload(app, runtime, agent_did)

    # Add healthz-specific fields
    payload["status"] = "ok" if runtime["strict_ready"] else "degraded"
    payload["ready"] = runtime["strict_ready"]
    payload["uptime_seconds"] = round(monotonic() - _start_time, 2)

    # Remove platform_release for healthz (lighter payload)
    payload["system"].pop("platform_release", None)

    status_code = 200 if runtime["strict_ready"] else 503
    return JSONResponse(payload, status_code=status_code)
