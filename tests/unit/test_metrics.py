"""Unit tests for Prometheus metrics endpoint."""

from __future__ import annotations

import pytest

from bindu.server.metrics import PrometheusMetrics


@pytest.fixture
def metrics():
    """Create a fresh metrics instance for each test."""
    return PrometheusMetrics()


def test_metrics_record_http_request(metrics):
    """Test recording HTTP requests."""
    metrics.record_http_request("GET", "/health", "200", 0.05)
    metrics.record_http_request("POST", "/", "200", 0.15)
    metrics.record_http_request("GET", "/health", "200", 0.03)

    output = metrics.generate_prometheus_text()

    assert (
        'http_requests_total{method="GET",endpoint="/health",status="200"} 2' in output
    )
    assert 'http_requests_total{method="POST",endpoint="/",status="200"} 1' in output
    assert "http_request_duration_seconds" in output


def test_metrics_histogram_buckets(metrics):
    """Test histogram bucket counting."""
    metrics.record_http_request("GET", "/test", "200", 0.05)
    metrics.record_http_request("GET", "/test", "200", 0.3)
    metrics.record_http_request("GET", "/test", "200", 0.7)
    metrics.record_http_request("GET", "/test", "200", 1.5)

    output = metrics.generate_prometheus_text()

    assert 'http_request_duration_seconds_bucket{le="0.1"} 1' in output
    assert 'http_request_duration_seconds_bucket{le="0.5"} 2' in output
    assert 'http_request_duration_seconds_bucket{le="1.0"} 3' in output
    assert 'http_request_duration_seconds_bucket{le="+Inf"} 4' in output
    # Check for sum (allow for floating-point precision: 2.5 or 2.6)
    assert "http_request_duration_seconds_sum 2." in output
    assert "http_request_duration_seconds_count 4" in output


def test_metrics_agent_tasks(metrics):
    """Test agent task metrics."""
    agent_id = "test-agent-123"

    metrics.set_agent_tasks_active(agent_id, 3)
    metrics.increment_agent_tasks_completed(agent_id, "success")
    metrics.increment_agent_tasks_completed(agent_id, "success")
    metrics.increment_agent_tasks_completed(agent_id, "failed")

    output = metrics.generate_prometheus_text()

    assert f'agent_tasks_active{{agent_id="{agent_id}"}} 3' in output
    assert (
        f'agent_tasks_completed_total{{agent_id="{agent_id}",status="success"}} 2'
        in output
    )
    assert (
        f'agent_tasks_completed_total{{agent_id="{agent_id}",status="failed"}} 1'
        in output
    )


def test_metrics_prometheus_format(metrics):
    """Test Prometheus text format output."""
    metrics.record_http_request("GET", "/health", "200", 0.1)

    output = metrics.generate_prometheus_text()

    assert "# HELP http_requests_total Total number of HTTP requests" in output
    assert "# TYPE http_requests_total counter" in output
    assert "# HELP http_request_duration_seconds HTTP request latency" in output
    assert "# TYPE http_request_duration_seconds histogram" in output


def test_metrics_thread_safety(metrics):
    """Test that metrics collection is thread-safe."""
    import concurrent.futures

    def record_request():
        for _ in range(10):
            metrics.record_http_request("GET", "/test", "200", 0.1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(record_request) for _ in range(5)]
        concurrent.futures.wait(futures)

    output = metrics.generate_prometheus_text()
    assert (
        'http_requests_total{method="GET",endpoint="/test",status="200"} 50' in output
    )


def test_metrics_prometheus_format_headers():
    """Test that metrics are properly formatted for Prometheus."""
    metrics = PrometheusMetrics()
    metrics.record_http_request("GET", "/test", "200", 0.1)

    output = metrics.generate_prometheus_text()

    # Verify Prometheus format structure
    assert "# HELP http_requests_total" in output
    assert "# TYPE http_requests_total counter" in output
    assert "# HELP http_request_duration_seconds" in output
    assert "# TYPE http_request_duration_seconds histogram" in output
    assert "# HELP http_requests_in_flight" in output
    assert "# TYPE http_requests_in_flight gauge" in output
