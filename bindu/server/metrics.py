"""Prometheus metrics collection for Bindu server monitoring.

This module provides metrics collection for HTTP requests, latency, and agent tasks.
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock

from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.metrics")


class PrometheusMetrics:
    """Prometheus metrics collector for Bindu server."""

    def __init__(self):
        """Initialize metrics collector."""
        self._lock = Lock()

        # HTTP request counters: {(method, endpoint, status): count}
        self._http_requests: dict[tuple[str, str, str], int] = defaultdict(int)

        # HTTP request duration histograms: {bucket_le: count}
        # Buckets: 0.1s, 0.5s, 1.0s, +Inf
        self._duration_buckets = [0.1, 0.5, 1.0, float("inf")]
        self._duration_counts: dict[float, int] = defaultdict(int)
        self._duration_sum = 0.0
        self._duration_total_count = 0

        # Agent task gauges: {agent_id: active_count}
        self._agent_tasks_active: dict[str, int] = defaultdict(int)

        # Agent task completion counters: {(agent_id, status): count}
        self._agent_tasks_completed: dict[tuple[str, str], int] = defaultdict(int)

        # Task duration histogram: {bucket_le: count}
        # Buckets: 1s, 5s, 10s, 30s, 60s, +Inf
        self._task_duration_buckets = [1.0, 5.0, 10.0, 30.0, 60.0, float("inf")]
        self._task_duration_counts: dict[tuple[str, str, float], int] = defaultdict(
            int
        )  # (agent_id, status, bucket)
        self._task_duration_sum: dict[tuple[str, str], float] = defaultdict(
            float
        )  # (agent_id, status)
        self._task_duration_total_count: dict[tuple[str, str], int] = defaultdict(
            int
        )  # (agent_id, status)

        # Error tracking: {(agent_id, error_type): count}
        self._agent_errors: dict[tuple[str, str], int] = defaultdict(int)

        # Request/Response size metrics
        self._http_request_size_sum = 0.0
        self._http_request_size_count = 0
        self._http_response_size_sum = 0.0
        self._http_response_size_count = 0
        self._http_requests_in_flight = 0

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: str,
        duration: float,
        request_size: int = 0,
        response_size: int = 0,
    ) -> None:
        """Record an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Request endpoint path
            status: HTTP status code
            duration: Request duration in seconds
            request_size: Request body size in bytes
            response_size: Response body size in bytes
        """
        with self._lock:
            # Increment request counter
            key = (method, endpoint, status)
            self._http_requests[key] += 1

            # Record duration in histogram buckets
            for bucket in self._duration_buckets:
                if duration <= bucket:
                    self._duration_counts[bucket] += 1

            self._duration_sum += duration
            self._duration_total_count += 1

            # Record request/response sizes
            if request_size > 0:
                self._http_request_size_sum += request_size
                self._http_request_size_count += 1
            if response_size > 0:
                self._http_response_size_sum += response_size
                self._http_response_size_count += 1

    def set_agent_tasks_active(self, agent_id: str, count: int) -> None:
        """Set the number of active tasks for an agent.

        Args:
            agent_id: Agent identifier
            count: Number of active tasks
        """
        with self._lock:
            self._agent_tasks_active[agent_id] = count

    def increment_agent_tasks_completed(self, agent_id: str, status: str) -> None:
        """Increment completed task counter for an agent.

        Args:
            agent_id: Agent identifier
            status: Task completion status (success, failed, canceled)
        """
        with self._lock:
            key = (agent_id, status)
            self._agent_tasks_completed[key] += 1

    def record_task_duration(self, agent_id: str, status: str, duration: float) -> None:
        """Record task execution duration.

        Args:
            agent_id: Agent identifier
            status: Task completion status (success, failed, canceled)
            duration: Task duration in seconds
        """
        with self._lock:
            key = (agent_id, status)

            # Record in histogram buckets
            for bucket in self._task_duration_buckets:
                if duration <= bucket:
                    bucket_key = (agent_id, status, bucket)
                    self._task_duration_counts[bucket_key] += 1

            self._task_duration_sum[key] += duration
            self._task_duration_total_count[key] += 1

    def increment_agent_error(self, agent_id: str, error_type: str) -> None:
        """Increment error counter for an agent.

        Args:
            agent_id: Agent identifier
            error_type: Type of error (e.g., 'timeout', 'validation', 'execution')
        """
        with self._lock:
            key = (agent_id, error_type)
            self._agent_errors[key] += 1

    @staticmethod
    def _format_bucket(bucket: float) -> str:
        """Format bucket value for Prometheus output.

        Args:
            bucket: Bucket upper bound value

        Returns:
            Formatted bucket string ('+Inf' for infinity, otherwise string representation)
        """
        return "+Inf" if bucket == float("inf") else str(bucket)

    @staticmethod
    def _add_metric_header(
        lines: list[str], metric_name: str, help_text: str, metric_type: str
    ) -> None:
        """Add Prometheus metric header lines.

        Args:
            lines: List to append header lines to
            metric_name: Name of the metric
            help_text: Help text describing the metric
            metric_type: Prometheus metric type (counter, gauge, histogram, summary)
        """
        lines.append(f"# HELP {metric_name} {help_text}")
        lines.append(f"# TYPE {metric_name} {metric_type}")

    def increment_requests_in_flight(self) -> None:
        """Increment the number of concurrent requests."""
        with self._lock:
            self._http_requests_in_flight += 1

    def decrement_requests_in_flight(self) -> None:
        """Decrement the number of concurrent requests."""
        with self._lock:
            self._http_requests_in_flight = max(0, self._http_requests_in_flight - 1)

    def generate_prometheus_text(self) -> str:
        """Generate Prometheus text format metrics.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        with self._lock:
            # HTTP requests total
            self._add_metric_header(
                lines, "http_requests_total", "Total number of HTTP requests", "counter"
            )
            for (method, endpoint, status), count in sorted(
                self._http_requests.items()
            ):
                lines.append(
                    f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
                )

            # HTTP request duration
            lines.append("")
            self._add_metric_header(
                lines,
                "http_request_duration_seconds",
                "HTTP request latency",
                "histogram",
            )
            for bucket in self._duration_buckets:
                count = self._duration_counts[bucket]
                bucket_str = self._format_bucket(bucket)
                lines.append(
                    f'http_request_duration_seconds_bucket{{le="{bucket_str}"}} {count}'
                )
            lines.append(f"http_request_duration_seconds_sum {self._duration_sum:.1f}")
            lines.append(
                f"http_request_duration_seconds_count {self._duration_total_count}"
            )

            # Agent tasks active
            if self._agent_tasks_active:
                lines.append("")
                self._add_metric_header(
                    lines, "agent_tasks_active", "Currently active tasks", "gauge"
                )
                for agent_id, count in sorted(self._agent_tasks_active.items()):
                    lines.append(f'agent_tasks_active{{agent_id="{agent_id}"}} {count}')

            # Agent tasks completed
            if self._agent_tasks_completed:
                lines.append("")
                self._add_metric_header(
                    lines,
                    "agent_tasks_completed_total",
                    "Total completed tasks",
                    "counter",
                )
                for (agent_id, status), count in sorted(
                    self._agent_tasks_completed.items()
                ):
                    lines.append(
                        f'agent_tasks_completed_total{{agent_id="{agent_id}",status="{status}"}} {count}'
                    )

            # Task duration histogram
            if self._task_duration_total_count:
                lines.append("")
                self._add_metric_header(
                    lines,
                    "task_duration_seconds",
                    "Task execution duration",
                    "histogram",
                )

                # Group by agent_id and status for histogram output
                agent_status_pairs = set(
                    (agent_id, status)
                    for (agent_id, status, _) in self._task_duration_counts.keys()
                )

                for agent_id, status in sorted(agent_status_pairs):
                    for bucket in self._task_duration_buckets:
                        bucket_key = (agent_id, status, bucket)
                        count = self._task_duration_counts.get(bucket_key, 0)
                        bucket_str = self._format_bucket(bucket)
                        lines.append(
                            f'task_duration_seconds_bucket{{agent_id="{agent_id}",status="{status}",le="{bucket_str}"}} {count}'
                        )

                    key = (agent_id, status)
                    duration_sum = self._task_duration_sum.get(key, 0.0)
                    duration_count = self._task_duration_total_count.get(key, 0)
                    lines.append(
                        f'task_duration_seconds_sum{{agent_id="{agent_id}",status="{status}"}} {duration_sum:.1f}'
                    )
                    lines.append(
                        f'task_duration_seconds_count{{agent_id="{agent_id}",status="{status}"}} {duration_count}'
                    )

            # Agent errors
            if self._agent_errors:
                lines.append("")
                self._add_metric_header(
                    lines, "agent_errors_total", "Total errors by type", "counter"
                )
                for (agent_id, error_type), count in sorted(self._agent_errors.items()):
                    lines.append(
                        f'agent_errors_total{{agent_id="{agent_id}",error_type="{error_type}"}} {count}'
                    )

            # Request size metrics
            if self._http_request_size_count > 0:
                lines.append("")
                self._add_metric_header(
                    lines,
                    "http_request_size_bytes",
                    "HTTP request body size",
                    "summary",
                )
                lines.append(
                    f"http_request_size_bytes_sum {self._http_request_size_sum:.0f}"
                )
                lines.append(
                    f"http_request_size_bytes_count {self._http_request_size_count}"
                )

            # Response size metrics
            if self._http_response_size_count > 0:
                lines.append("")
                self._add_metric_header(
                    lines,
                    "http_response_size_bytes",
                    "HTTP response body size",
                    "summary",
                )
                lines.append(
                    f"http_response_size_bytes_sum {self._http_response_size_sum:.0f}"
                )
                lines.append(
                    f"http_response_size_bytes_count {self._http_response_size_count}"
                )

            # Requests in flight
            lines.append("")
            self._add_metric_header(
                lines,
                "http_requests_in_flight",
                "Current number of HTTP requests being processed",
                "gauge",
            )
            lines.append(f"http_requests_in_flight {self._http_requests_in_flight}")

        return "\n".join(lines) + "\n"


# Global metrics instance
_metrics_instance: PrometheusMetrics | None = None
_metrics_init_lock = Lock()


def get_metrics() -> PrometheusMetrics:
    """Get or create the global metrics instance.

    Returns:
        PrometheusMetrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        with _metrics_init_lock:
            if _metrics_instance is None:
                _metrics_instance = PrometheusMetrics()
    return _metrics_instance
