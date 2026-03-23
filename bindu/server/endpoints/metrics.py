"""Prometheus metrics endpoint for monitoring."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from bindu.server.applications import BinduApplication
from bindu.server.metrics import get_metrics
from bindu.utils.logging import get_logger
from .utils import get_agent_did

logger = get_logger("bindu.server.endpoints.metrics")

# Constants - using string literals that match TaskState
ACTIVE_TASK_STATUSES: tuple[str, str, str] = ("submitted", "working", "input-required")
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


async def _update_agent_metrics(app: BinduApplication) -> None:
    """Update agent task metrics from the application state.

    Args:
        app: BinduApplication instance
    """
    if not app.task_manager or not app._storage:
        return

    metrics = get_metrics()

    # Get agent ID from manifest
    agent_id = get_agent_did(app)
    if agent_id:
        try:
            # Count active tasks (submitted, working, input-required)
            from typing import cast
            from bindu.common.protocol.types import TaskState

            submitted = await app._storage.count_tasks(
                status=cast(TaskState, ACTIVE_TASK_STATUSES[0])
            )
            working = await app._storage.count_tasks(
                status=cast(TaskState, ACTIVE_TASK_STATUSES[1])
            )
            input_required = await app._storage.count_tasks(
                status=cast(TaskState, ACTIVE_TASK_STATUSES[2])
            )

            active_count = submitted + working + input_required
            metrics.set_agent_tasks_active(agent_id, active_count)
        except Exception as e:
            logger.debug(f"Failed to update agent metrics: {e}")


async def metrics_endpoint(app: BinduApplication, request: Request) -> Response:
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.

    Metrics exposed:
    - http_requests_total: Total number of HTTP requests by method, endpoint, and status
    - http_request_duration_seconds: HTTP request latency histogram
    - agent_tasks_active: Currently active tasks per agent
    - agent_tasks_completed_total: Total completed tasks per agent and status
    """
    logger.debug("Metrics endpoint called")

    # Update agent metrics from current state
    await _update_agent_metrics(app)

    # Get metrics instance and generate Prometheus text
    metrics = get_metrics()
    prometheus_text = metrics.generate_prometheus_text()

    return Response(
        content=prometheus_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers=NO_CACHE_HEADERS,
    )
