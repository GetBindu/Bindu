---
description: Deploy Bindu agents locally with in-memory backends
---

# Bindu Deployment Workflow

Quick local deployment using in-memory storage and scheduler - perfect for development and testing.

## Quick Start

```bash
# One-line deployment with tunnel
uv run bindu serve --launch
```

That's it! Your agent is running with:
- ✅ In-memory storage (no database needed)
- ✅ In-memory scheduler (no Redis needed)
- ✅ Public tunnel URL (accessible from anywhere)

---

## Step 1: Pre-Deployment Checks

```bash
# Verify tests pass
uv run pytest

# Check version
uv run bindu --version
```

---

## Step 2: Deploy Agent

### Basic Deployment (No Tunnel)

```bash
# Start agent on localhost:3773
uv run bindu serve
```

### With Public Tunnel (Recommended)

```bash
# Start with automatic tunnel
uv run bindu serve --launch

# Look for output:
# Tunnel URL: https://xxx.tunnel.getbindu.com
```

### Custom Configuration

```bash
# Custom port
PORT=8080 uv run bindu serve --launch

# Explicit backends (default for local)
STORAGE_BACKEND=memory \
SCHEDULER_BACKEND=memory \
uv run bindu serve --launch
```

---

## Step 3: Verify Deployment

```bash
# Health check
curl http://localhost:3773/health | jq

# Agent card
curl http://localhost:3773/.well-known/agent.json | jq

# Skills list
curl http://localhost:3773/agent/skills | jq
```

Expected health response:

```json
{
  "status": "ok",
  "ready": true,
  "uptime_seconds": 10.5,
  "version": "2026.8.5",
  "health": "healthy",
  "runtime": {
    "storage_backend": "MemoryStorage",
    "scheduler_backend": "MemoryScheduler",
    "task_manager_running": true
  },
  "application": {
    "penguin_id": "abc123..."
  }
}
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 3773
lsof -i :3773

# Kill process
kill -9 <PID>

# Or use different port
PORT=8080 uv run bindu serve
```

### Agent Won't Start

```bash
# Check logs for errors
uv run bindu serve --debug

# Verify dependencies
uv sync

# Run health diagnostics
uv run pytest tests/unit/test_applications.py -v
```

---

## Advanced: Production Deployment

For production with PostgreSQL + Redis, see [Production Deployment Guide](../docs/DEPLOYMENT.md).

Quick reference:

```bash
# Set environment
export DATABASE_URL="postgresql://<username>:<password>@host:5432/bindu"
export REDIS_URL="redis://host:6379/0"
export STORAGE_BACKEND=postgres
export SCHEDULER_BACKEND=redis

# Run migrations
uv run alembic upgrade head

# Start server
uv run bindu serve
```

---

## Next Steps

After deployment:

1. Test agent functionality via tunnel URL
2. Check `/health` endpoint
3. View agent card at `/.well-known/agent.json`
4. Test A2A protocol with example clients
