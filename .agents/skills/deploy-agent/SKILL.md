---
name: deploy-agent
description: Deploy Bindu agents to various environments with safety checks and verification
---

# Deploy Agent Skill

## Overview

Deploy a Bindu agent to a target environment (local, staging, production) with comprehensive safety checks.

## Inputs

- Environment name (local, staging, production)
- Agent configuration file path
- Optional: deployment strategy (rolling, blue-green, canary)

## Safety

- Never deploy without passing tests
- Verify environment variables before deployment
- Run health checks after deployment
- Generate deployment artifacts
- Support rollback if deployment fails

## Execution Contract

1. Validate environment configuration
2. Run pre-deployment checks
3. Apply database migrations
4. Deploy agent
5. Verify deployment health
6. Generate deployment record

## Steps

### 1. Pre-Deployment Validation

```bash
# Check environment
ENVIRONMENT=$1
if [ -z "$ENVIRONMENT" ]; then
    echo "Error: Environment required (local, staging, production)"
    exit 1
fi

# Validate tests pass
echo "==> Running tests..."
uv run pytest || { echo "❌ Tests failed"; exit 1; }

# Validate pre-commit hooks
echo "==> Running pre-commit hooks..."
uv run pre-commit run --all-files || { echo "❌ Pre-commit hooks failed"; exit 1; }

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️ Warning: Uncommitted changes detected"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
```

### 2. Environment Configuration

```bash
# Load environment-specific config
case $ENVIRONMENT in
    local)
        export STORAGE_BACKEND=memory
        export SCHEDULER_BACKEND=memory
        export PORT=3773
        ;;
    staging)
        export STORAGE_BACKEND=postgres
        export SCHEDULER_BACKEND=redis
        export DATABASE_URL=$STAGING_DATABASE_URL
        export REDIS_URL=$STAGING_REDIS_URL
        export PORT=3773
        ;;
    production)
        export STORAGE_BACKEND=postgres
        export SCHEDULER_BACKEND=redis
        export DATABASE_URL=$PROD_DATABASE_URL
        export REDIS_URL=$PROD_REDIS_URL
        export PORT=8080
        ;;
    *)
        echo "Error: Unknown environment $ENVIRONMENT"
        exit 1
        ;;
esac

# Verify required variables
required_vars=("STORAGE_BACKEND" "SCHEDULER_BACKEND")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var not set"
        exit 1
    fi
done
```

### 3. Database Migrations

```bash
# Run migrations for postgres backend
if [ "$STORAGE_BACKEND" = "postgres" ]; then
    echo "==> Running database migrations..."

    # Check current migration
    CURRENT=$(uv run alembic current 2>&1)
    echo "Current migration: $CURRENT"

    # Upgrade to head
    uv run alembic upgrade head || { echo "❌ Migration failed"; exit 1; }

    # Verify migration
    NEW_CURRENT=$(uv run alembic current 2>&1)
    echo "New migration: $NEW_CURRENT"
fi
```

### 4. Deploy Agent

```bash
# Local deployment
if [ "$ENVIRONMENT" = "local" ]; then
    echo "==> Starting local agent with tunnel..."
    uv run bindu serve --launch &
    AGENT_PID=$!
    echo "Agent PID: $AGENT_PID"
    sleep 5
fi

# Staging/Production deployment
if [ "$ENVIRONMENT" != "local" ]; then
    echo "==> Deploying to $ENVIRONMENT..."

    # Docker deployment
    if command -v docker &> /dev/null; then
        # Build image
        docker build -t bindu-agent:$ENVIRONMENT .

        # Stop old container
        docker stop bindu-agent-$ENVIRONMENT 2>/dev/null || true
        docker rm bindu-agent-$ENVIRONMENT 2>/dev/null || true

        # Start new container
        docker run -d \
            --name bindu-agent-$ENVIRONMENT \
            -p $PORT:8080 \
            -e DATABASE_URL="$DATABASE_URL" \
            -e REDIS_URL="$REDIS_URL" \
            -e STORAGE_BACKEND="$STORAGE_BACKEND" \
            -e SCHEDULER_BACKEND="$SCHEDULER_BACKEND" \
            bindu-agent:$ENVIRONMENT

        CONTAINER_ID=$(docker ps -qf "name=bindu-agent-$ENVIRONMENT")
        echo "Container ID: $CONTAINER_ID"
    else
        # Direct deployment
        uv run bindu serve &
        AGENT_PID=$!
        echo "Agent PID: $AGENT_PID"
    fi

    sleep 10
fi
```

### 5. Health Verification

```bash
# Determine health URL
if [ "$ENVIRONMENT" = "local" ]; then
    HEALTH_URL="http://localhost:3773/health"
else
    HEALTH_URL="http://localhost:$PORT/health"
fi

# Wait for agent to be ready
echo "==> Waiting for agent to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf $HEALTH_URL > /dev/null 2>&1; then
        echo "✅ Agent is healthy"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Agent failed to become healthy"
    exit 1
fi

# Get health details
HEALTH_RESPONSE=$(curl -s $HEALTH_URL)
echo "Health response:"
echo "$HEALTH_RESPONSE" | jq .
```

### 6. Verify Deployment

```bash
# Check agent card
echo "==> Verifying agent card..."
curl -sf http://localhost:$PORT/.well-known/agent.json | jq . || echo "⚠️ Agent card not available"

# Check skills
echo "==> Verifying skills..."
curl -sf http://localhost:$PORT/agent/skills | jq . || echo "⚠️ Skills not available"

# Check metrics
echo "==> Checking metrics..."
curl -sf http://localhost:$PORT/metrics | head -n 10 || echo "⚠️ Metrics not available"
```

### 7. Generate Deployment Record

Create `.local/deployment.json`:

```json
{
  "environment": "production",
  "timestamp": "2026-02-19T07:00:00Z",
  "version": "2026.8.5",
  "commit": "abc1234",
  "deployment_id": "deploy-20260219-070000",
  "status": "success",
  "health": {
    "status": "ok",
    "ready": true,
    "uptime_seconds": 10.5
  },
  "configuration": {
    "storage_backend": "postgres",
    "scheduler_backend": "redis",
    "port": 8080
  },
  "verification": {
    "health_check": "pass",
    "agent_card": "pass",
    "skills": "pass",
    "metrics": "pass"
  }
}
```

## Rollback Procedure

If deployment fails:

```bash
# Stop new deployment
if [ -n "$CONTAINER_ID" ]; then
    docker stop $CONTAINER_ID
    docker rm $CONTAINER_ID
fi

if [ -n "$AGENT_PID" ]; then
    kill $AGENT_PID
fi

# Rollback database
if [ "$STORAGE_BACKEND" = "postgres" ]; then
    uv run alembic downgrade -1
fi

# Restore previous version
git checkout <previous-tag>
uv sync

# Redeploy
/skill deploy-agent $ENVIRONMENT
```

## Output Format

```markdown
# Deployment Report

## Environment
- Target: production
- Version: 2026.8.5
- Commit: abc1234

## Pre-Deployment
✅ Tests passed
✅ Pre-commit hooks passed
✅ Environment configured

## Deployment
✅ Database migrations applied
✅ Agent deployed (Container: xyz123)
✅ Health check passed

## Verification
✅ Agent card available
✅ Skills endpoint responding
✅ Metrics endpoint responding

## Status
🎉 Deployment successful!

## Next Steps
1. Monitor logs for errors
2. Check metrics dashboard
3. Test agent functionality
```

## Artifacts Generated

- `.local/deployment.json` - Deployment metadata
- `.local/health-check.json` - Health check results
- `.local/deployment-log.txt` - Deployment logs

## Guardrails

- Never deploy without passing tests
- Always run migrations before deployment
- Always verify health after deployment
- Generate deployment record
- Support rollback on failure

## Example Usage

```bash
# Deploy to local
/skill deploy-agent local

# Deploy to staging
/skill deploy-agent staging

# Deploy to production
/skill deploy-agent production
```
