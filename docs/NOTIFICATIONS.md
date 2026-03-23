# Push Notifications (Webhooks)

Bindu supports **real-time webhook notifications** for long-running tasks, following the [A2A Protocol specification](https://a2a-protocol.org/latest/specification/). Receive push notifications about task state changes and artifact generation without polling.

## Configuration

### Environment Variables

```bash
# Global webhook configuration
GLOBAL_WEBHOOK_URL=http://your-server.com/webhooks/task-updates
GLOBAL_WEBHOOK_TOKEN=your_secret_token_here
```

### Agent Configuration

```python
config = {
    "name": "my_agent",
    "capabilities": {"push_notifications": True},
    # Webhook URL and token loaded from environment variables
}

bindufy(config, handler)
```

### Per-Task Webhook Override

Clients can override the global webhook for specific tasks:

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {...},
      "configuration": {
        "webhook_url": "http://custom-endpoint.com/webhook",
        "webhook_token": "custom_token"
      }
    }
  }'
```

## Event Types

### Status Update Event

Sent when task state changes (submitted → working → completed):

```json
{
  "kind": "status-update",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": {
    "state": "working",
    "timestamp": "2026-02-11T12:00:00Z"
  },
  "final": false
}
```

**States:**
- `submitted` - Task received and queued
- `working` - Task is being processed
- `completed` - Task finished successfully
- `failed` - Task encountered an error
- `input_required` - Task needs additional input

### Artifact Update Event

Sent when artifacts (outputs) are generated:

```json
{
  "kind": "artifact-update",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "artifact": {
    "artifact_id": "456e7890-e89b-12d3-a456-426614174001",
    "name": "results.json",
    "parts": [
      {
        "kind": "text",
        "text": "Processing complete"
      }
    ]
  }
}
```

## Implementing a Webhook Receiver

### Basic FastAPI Example

```python
from fastapi import FastAPI, Request, Header, HTTPException

app = FastAPI()

@app.post("/webhooks/task-updates")
async def handle_task_update(
    request: Request,
    authorization: str = Header(None)
):
    # Verify token
    if authorization != "Bearer your_secret_token_here":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse event
    event = await request.json()

    # Handle different event types
    if event["kind"] == "status-update":
        task_id = event["task_id"]
        state = event["status"]["state"]
        print(f"Task {task_id} is now {state}")

        if state == "completed":
            # Task finished - fetch results
            pass

    elif event["kind"] == "artifact-update":
        artifact = event["artifact"]
        print(f"Artifact generated: {artifact['name']}")

    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Express.js Example

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhooks/task-updates', (req, res) => {
  // Verify token
  const token = req.headers.authorization;
  if (token !== 'Bearer your_secret_token_here') {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const event = req.body;

  // Handle events
  if (event.kind === 'status-update') {
    console.log(`Task ${event.task_id}: ${event.status.state}`);
  } else if (event.kind === 'artifact-update') {
    console.log(`Artifact: ${event.artifact.name}`);
  }

  res.json({ status: 'received' });
});

app.listen(8000, () => {
  console.log('Webhook receiver running on port 8000');
});
```

## Security

### Authentication

Always verify the webhook token:

```python
# Check Authorization header
if authorization != f"Bearer {expected_token}":
    raise HTTPException(status_code=401)
```


### Event Processing

```python
@app.post("/webhooks/task-updates")
async def handle_task_update(request: Request):
    # Return 200 immediately
    event = await request.json()

    # Process asynchronously
    asyncio.create_task(process_event(event))

    return {"status": "received"}

async def process_event(event):
    # Long-running processing here
    pass
```

## Examples

See complete examples:
- `examples/webhook_client_example.py` - Webhook receiver
- `examples/echo_agent_with_webhooks.py` - Agent with webhooks

## Related Documentation

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [Task Management](https://docs.getbindu.com/bindu/tasks/overview)
