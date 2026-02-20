# Streaming (Server-Sent Events)

Bindu supports **real-time streaming responses** via Server-Sent Events (SSE), following the [A2A Protocol `message/stream` method](https://a2a-protocol.org/latest/specification/). Stream agent output token-by-token to clients as it's generated, instead of waiting for the full response.

## Configuration

### Agent Configuration

Enable streaming in your agent's capabilities:

```python
config = {
    "name": "my_streaming_agent",
    "capabilities": {"streaming": True},
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
    },
}

bindufy(config, handler)
```

### Handler Pattern

Return a **generator** (sync or async) from your handler to enable streaming. Each yielded value becomes an SSE chunk:

```python
# Sync generator
def handler(messages):
    for token in llm.stream(messages[-1]["content"]):
        yield token

# Async generator
async def handler(messages):
    async for token in llm.astream(messages[-1]["content"]):
        yield token
```

Non-generator return values (strings, lists) also work — they're delivered as a single artifact event.

## SSE Event Format

The streaming endpoint produces a sequence of SSE events. Each event conforms to the A2A Protocol's `TaskStatusUpdateEvent` or `TaskArtifactUpdateEvent` types, serialized as a `data:` line:

### Status Events (`TaskStatusUpdateEvent`)

Sent when task state changes:

```
data: {"kind":"status-update","task_id":"...","context_id":"...","status":{"state":"working","timestamp":"2026-02-14T12:00:00+00:00"},"final":false}

data: {"kind":"status-update","task_id":"...","context_id":"...","status":{"state":"completed","timestamp":"2026-02-14T12:00:01+00:00"},"final":true}
```

### Artifact Events (`TaskArtifactUpdateEvent`)

Sent for each streamed chunk:

```
data: {"kind":"artifact-update","task_id":"...","context_id":"...","artifact":{"artifact_id":"...","name":"streaming_response","parts":[{"kind":"text","text":"Hello"}]},"append":true,"last_chunk":false}
```

After the last content chunk, a final marker event is emitted with `"last_chunk": true` and empty text, signaling to clients that the artifact is complete:

```
data: {"kind":"artifact-update","task_id":"...","context_id":"...","artifact":{"artifact_id":"...","name":"streaming_response","parts":[{"kind":"text","text":""}]},"append":true,"last_chunk":true}
```

### Event Sequence

A typical streaming session produces:

1. `status-update` — state: `working`, final: `false`
2. `artifact-update` — chunk 1, append: `true`, last_chunk: `false`
3. `artifact-update` — chunk 2, append: `true`, last_chunk: `false`
4. ...
5. `artifact-update` — empty marker, append: `true`, last_chunk: `true`
6. `status-update` — state: `completed`, final: `true`

All chunks share the same `artifact_id`, enabling client-side reassembly.

## Client Usage

### curl

```bash
curl -N -X POST http://localhost:3773/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/stream",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Tell me about streaming"}],
        "messageId": "msg-1"
      }
    }
  }'
```

### Python (httpx)

```python
import httpx
import json

url = "http://localhost:3773/a2a"
payload = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/stream",
    "params": {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": "Hello"}],
            "messageId": "msg-1",
        }
    },
}

with httpx.stream("POST", url, json=payload) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            kind = event.get("kind")

            if kind == "status-update":
                state = event["status"]["state"]
                print(f"[status] {state}")

            elif kind == "artifact-update":
                if event.get("last_chunk"):
                    continue  # Skip the empty last_chunk marker
                text = event["artifact"]["parts"][0]["text"]
                print(text, end="", flush=True)

    print()  # Final newline
```

### JavaScript (fetch + ReadableStream)

```javascript
const response = await fetch("http://localhost:3773/a2a", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    jsonrpc: "2.0",
    id: "1",
    method: "message/stream",
    params: {
      message: {
        role: "user",
        parts: [{ kind: "text", text: "Hello" }],
        messageId: "msg-1",
      },
    },
  }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop();

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const event = JSON.parse(line.slice(6));

      if (event.kind === "artifact-update" && !event.last_chunk) {
        const text = event.artifact.parts[0].text;
        process.stdout.write(text);
      } else if (event.kind === "status-update") {
        console.log(`\n[status] ${event.status.state}`);
      }
    }
  }
}
```

## Architecture

Streaming flows through the same worker pipeline as `message/send`:

```
Client  →  a2a_protocol.py  →  MessageHandlers.stream_message()
                                        │
                          ┌─────────────┤
                          ▼             ▼
                   submit_task()   StreamingResponse
                   (storage)       (_stream_generator)
                                        │
                          ┌─────────────┤
                          ▼             ▼
                   build_history()  manifest.run()
                   (via worker)     (generator)
                                        │
                                   yield chunks → SSE events
                                        │
                                   update_task()
                                   (artifacts + messages persisted)
```

Key design decisions:

- **Worker pipeline reuse**: Streaming uses `worker.build_complete_message_history()` and `worker.settle_payment()` — public APIs on ManifestWorker — ensuring consistent history building, system prompt injection, and payment settlement.
- **Incremental delivery**: Each generator yield becomes an SSE event immediately — no buffering.
- **Full persistence**: After streaming completes, the full response is persisted as artifacts and messages, identical to `message/send`.
- **Error resilience**: Exceptions during streaming emit a `failed` status event. Storage persistence errors in the error path are logged but don't prevent the client from receiving the failure notification.
- **Observability**: OpenTelemetry span covers the entire stream lifecycle with chunk count, duration, and error attributes. Active stream count is tracked via `bindu_active_tasks` metric.
- **Last chunk marker**: Generator paths emit a final `last_chunk=true` event after exhaustion, allowing clients to distinguish stream completion from a pause.

## Push Notifications with Streaming

Streaming supports push notification registration for long-running streams:

```json
{
  "method": "message/stream",
  "params": {
    "message": { "..." : "..." },
    "configuration": {
      "push_notification_config": {
        "url": "http://your-server.com/webhooks",
        "token": "secret"
      },
      "long_running": true
    }
  }
}
```

## Payment Integration (X402)

Streaming works with the X402 payment protocol. Payment is settled after all chunks have been delivered:

```
stream starts → chunks delivered → payment settled → completed event
```

This ensures clients only pay for successfully delivered responses.

## Examples

See complete examples:
- `examples/beginner/streaming_echo_agent.py` — Streaming agent that echoes word-by-word

## Related Documentation

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [Push Notifications](./NOTIFICATIONS.md)
- [Payment (X402)](./PAYMENT.md)
- [Storage](./STORAGE.md)
