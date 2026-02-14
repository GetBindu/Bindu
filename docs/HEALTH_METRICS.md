# Health Check & Metrics

Monitor your agent's health and performance with built-in endpoints.

## Health Check

Check if your agent is running and ready:

```bash
curl http://localhost:3773/health
```

**Response:**
```json
{
    "status": "ok",
    "uptime_seconds": 2504.32,
    "version": "2026.6.7.dev65+g6742cd6eb.d20260210",
    "ready": true
}
```

**Response Fields:**
- `status` - Overall health status (`ok` or `error`)
- `uptime_seconds` - Time since agent started
- `version` - Bindu version number
- `ready` - Whether agent is ready to accept requests

## Metrics API

Get Prometheus-compatible metrics for monitoring:

```bash
curl http://localhost:3773/metrics
```

**Available Metrics:**
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histogram
- `agent_tasks_active` - Currently active tasks gauge
- `http_response_size_bytes` - Response body size summary
- `http_requests_in_flight` - Current requests being processed

**Example Output:**
```prometheus
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health",status="200"} 1

# HELP agent_tasks_active Currently active tasks
# TYPE agent_tasks_active gauge
agent_tasks_active{agent_id="did:bindu:..."} 0

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 12
http_request_duration_seconds_count 12
```


## Related Documentation

- [Observability](./OBSERVABILITY.md) - OpenTelemetry and Sentry
- [Storage](./STORAGE.md) - PostgreSQL configuration
- [Scheduler](./SCHEDULER.md) - Redis configuration
