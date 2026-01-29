"""Prometheus metrics endpoint for monitoring."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from bindu.server.applications import BinduApplication
from bindu.server.metrics import get_metrics
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.endpoints.metrics")


async def _update_agent_metrics(app: BinduApplication) -> None:
    """Update agent task metrics from the application state.

    Args:
        app: BinduApplication instance
    """
    if not app.task_manager or not app._storage:
        return

    metrics = get_metrics()

    # Get agent ID from manifest
    if app.manifest and app.manifest.did_extension:
        agent_id = app.manifest.did_extension.did

        try:
            # Count active tasks from storage
            all_tasks = await app._storage.list_tasks()
            active_count = sum(
                1
                for task in all_tasks
                if task.state in ("submitted", "working", "input-required")
            )
            metrics.set_agent_tasks_active(agent_id, active_count)

            # Count completed tasks by status
            # Note: This counts from current session only, not historical totals
            # For historical totals, you'd need to track this separately
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
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
