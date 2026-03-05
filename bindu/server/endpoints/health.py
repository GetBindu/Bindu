"""Health check endpoint for service monitoring."""

from __future__ import annotations

from time import monotonic

from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu import __version__
from bindu.server.applications import BinduApplication
from bindu.utils.request_utils import handle_endpoint_errors, get_client_ip
from bindu.utils.logging import get_logger

import os
import platform
import sys


logger = get_logger("bindu.server.endpoints.health")

_start_time = monotonic()


@handle_endpoint_errors("health check")
async def health_endpoint(app: BinduApplication, request: Request) -> JSONResponse:
    """Comprehensive health check endpoint.

    Backward-compatible implementation.
    """
    # Measure endpoint execution time
    start = monotonic()

    client_ip = get_client_ip(request)
    logger.debug(f"Health check from {client_ip}")

    uptime = round(monotonic() - _start_time, 2)

    storage_type = type(app._storage).__name__ if app._storage else None
    scheduler_type = type(app._scheduler).__name__ if app._scheduler else None
    task_manager_running = app.task_manager.is_running if app.task_manager else False

    # Strict readiness
    strict_ready = all(
        [
            app._storage is not None,
            app._scheduler is not None,
            task_manager_running,
        ]
    )

    # Get agent DID if available
    agent_did = None
    if (
        app.manifest
        and hasattr(app.manifest, "did_extension")
        and app.manifest.did_extension
    ):
        agent_did = app.manifest.did_extension.did

    # Calculate response time in milliseconds
    response_time_ms = round((monotonic() - start) * 1000, 2)

    payload = {
        # Original fields (unchanged behavior)
        "status": "ok",
        "ready": True,
        "uptime_seconds": uptime,
        "version": __version__,
        # Observability extension
        "health": "healthy" if strict_ready else "degraded",
        "response_time_ms": response_time_ms,
        "runtime": {
            "storage_backend": storage_type,
            "scheduler_backend": scheduler_type,
            "task_manager_running": task_manager_running,
            "strict_ready": strict_ready,
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

    return JSONResponse(payload)


@handle_endpoint_errors("healthz check")
async def healthz_endpoint(app: BinduApplication, request: Request) -> JSONResponse:
    """Strict readiness check for Kubernetes readiness / liveness probes.

    Unlike ``/health`` (which always returns ``ready: true`` for backward
    compatibility), this endpoint returns ``ready: false`` and HTTP 503 until
    storage, scheduler, and task-manager are all confirmed running.

    Use ``/healthz`` as the Kubernetes ``readinessProbe`` target so that pods
    are only added to the load-balancer after full initialization.
    """
    storage_type = type(app._storage).__name__ if app._storage else None
    scheduler_type = type(app._scheduler).__name__ if app._scheduler else None
    task_manager_running = app.task_manager.is_running if app.task_manager else False

    strict_ready = all(
        [
            app._storage is not None,
            app._scheduler is not None,
            task_manager_running,
        ]
    )

    agent_did = None
    if (
        app.manifest
        and hasattr(app.manifest, "did_extension")
        and app.manifest.did_extension
    ):
        agent_did = app.manifest.did_extension.did

    payload = {
        "status": "ok" if strict_ready else "degraded",
        "ready": strict_ready,
        "uptime_seconds": round(monotonic() - _start_time, 2),
        "version": __version__,
        "health": "healthy" if strict_ready else "degraded",
        "runtime": {
            "storage_backend": storage_type,
            "scheduler_backend": scheduler_type,
            "task_manager_running": task_manager_running,
            "strict_ready": strict_ready,
        },
        "application": {
            "penguin_id": str(app.penguin_id),
            "agent_did": agent_did,
        },
        "system": {
            "python_version": sys.version.split()[0],
            "platform": platform.system(),
            "environment": os.getenv("ENV", "development"),
        },
    }

    status_code = 200 if strict_ready else 503
    return JSONResponse(payload, status_code=status_code)
