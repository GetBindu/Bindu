# Webhook Notification Agent

A **Bindu AI** agent that demonstrates event-driven webhook notifications when agent tasks complete.

## Overview

This example shows how to integrate Bindu agents with external systems using webhooks. When the agent processes a task, it automatically sends a structured HTTP POST request to a webhook endpoint with the task result, status, and metadata.

## How Webhook Notifications Work

1. **Agent receives messages** via the Bindu framework
2. **Processes the task** and generates a result
3. **Sends webhook notification** with:
   - Event type (`task_completed`)
   - Request ID (unique identifier for tracking)
   - User message content
   - ISO 8601 timestamp
   - Agent identifier
4. **Returns response** to the Bindu framework with webhook delivery status

## Project Structure

```
webhook_notification_agent/
├── agent.py                    # Main webhook notification agent
├── webhook_receiver_demo.py    # Local Flask server for testing
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Webhook URL (Environment Variables)

Set these environment variables before running:

```bash
# Linux/macOS
export WEBHOOK_URL="http://localhost:5000/webhook"
export WEBHOOK_TIMEOUT="5"

# Windows PowerShell
$env:WEBHOOK_URL = "http://localhost:5000/webhook"
$env:WEBHOOK_TIMEOUT = "5"
```

Default values are used if not set:
- `WEBHOOK_URL`: `http://localhost:5000/webhook`
- `WEBHOOK_TIMEOUT`: `5` seconds

## Running the Example

### Step 1: Start the Webhook Receiver

In one terminal, start the demo webhook receiver server:

```bash
python webhook_receiver_demo.py
```

You should see:

```
🚀 Starting Webhook Receiver Demo Server
======================================================================

Endpoints:
  • POST   http://localhost:5000/webhook  - Receive webhooks
  • GET    http://localhost:5000/history  - View webhook history
  • POST   http://localhost:5000/clear    - Clear history
  • GET    http://localhost:5000/         - Server info

======================================================================
Waiting for webhooks...
```

### Step 2: Run the Agent

In another terminal, test the agent locally:

```bash
python agent.py
```

Or integrate it with the Bindu framework following the [official Bindu documentation](https://github.com/bindu-ai/bindu).

### Step 3: View Webhook Notifications

The webhook receiver will display received notifications in real-time:

```
======================================================================
📬 WEBHOOK RECEIVED at 2026-03-05T10:30:45.123456Z
======================================================================
Event:      task.completed
Message:    Task completed successfully: Processed: Process this test task
Timestamp:  2026-03-05T10:30:45.123456Z
Request ID: a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5g6h7
Agent:      webhook_notification_agent

Metadata:
{
  "result": {
    "status": "success",
    "result": "Processed: Process this test task",
    "processed_messages": 3
  },
  "message_count": 3
}
======================================================================
```

## Testing with cURL

Send a test webhook manually:

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "task_completed",
    "request_id": "test-123",
    "message": "Manual test webhook",
    "timestamp": "2026-03-05T10:00:00Z",
    "agent": "webhook_notification_agent"
  }'
```

## Example Webhook Payload

The agent sends webhooks with this structure:

```json
{
  "event": "task_completed",
  "request_id": "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5g6h7",
  "message": "Process this webhook test task",
  "timestamp": "2026-03-05T10:30:45.123456Z",
  "agent": "webhook_notification_agent"
}
```

**Response from agent.py:**

```json
{
  "status": "success",
  "response": {
    "request_id": "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5g6h7",
    "webhook": {
      "status": "sent",
      "status_code": 200
    }
  }
}
```

## Features Demonstrated

✅ **Event-driven architecture** - Webhooks trigger on task completion  
✅ **Structured payloads** - Consistent JSON format with metadata  
✅ **Error handling** - Graceful handling of network and timeout errors  
✅ **Timeout protection** - Configurable timeout for webhook calls  
✅ **Request tracking** - Unique request IDs for correlation  
✅ **Bindu integration** - Official `bindufy` pattern  
✅ **Local testing** - Flask demo server for quick testing  

## Integration with External Services

Replace the `WEBHOOK_URL` with any webhook service:

- **Slack**: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`
- **Discord**: `https://discord.com/api/webhooks/YOUR/WEBHOOK/ID/TOKEN`
- **Teams**: `https://outlook.office.com/webhook/YOUR/WEBHOOK/URL`
- **Zapier**: `https://hooks.zapier.com/hooks/catch/YOUR/WEBHOOK/ID`
- **Custom API**: Any endpoint accepting POST requests

## Production Considerations

When deploying to production:

1. **Use environment variables** for webhook URLs
2. **Enable HTTPS** for secure webhook delivery
3. **Implement retry logic** for failed webhook deliveries
4. **Add authentication** (e.g., HMAC signatures, API keys)
5. **Log webhook events** for audit trails
6. **Monitor webhook performance** and failure rates
7. **Consider async webhooks** for high-volume scenarios

## Dependencies

- `bindu` - Bindu AI agent framework
- `requests` - HTTP library for webhook delivery
- `flask` - Web framework for demo receiver (dev only)

## License

This example is part of the Bindu AI framework and follows the same license terms.

## Contributing

Contributions are welcome! Please open an issue or pull request on the [Bindu GitHub repository](https://github.com/bindu-ai/bindu).

---

**Built with ❤️ for the Bindu AI community**
