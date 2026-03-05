# gRPC Transport Usage

This guide explains how to run and use Bindu with dual transport support:

- JSON-RPC over HTTP
- gRPC over HTTP/2

When enabled, both transports run at the same time.

## Prerequisites

- Python virtual environment activated
- Dependencies installed for this repository
- Generated protobuf stubs available in `bindu/grpc/`

If protobuf stubs are missing:

```bash
python scripts/generate_proto.py
```

## Enable gRPC

### PowerShell (Windows)

```powershell
$env:BINDU_GRPC_ENABLED="true"
$env:BINDU_GRPC_HOST="127.0.0.1"
$env:BINDU_GRPC_PORT="50051"
```

### Bash (Linux/macOS/Git Bash)

```bash
export BINDU_GRPC_ENABLED=true
export BINDU_GRPC_HOST=127.0.0.1
export BINDU_GRPC_PORT=50051
```

Optional settings:

- `BINDU_GRPC_MAX_WORKERS` (default: `10`)
- `BINDU_GRPC_TLS_ENABLED` (`true` / `false`)
- `BINDU_GRPC_TLS_CERT_PATH` (PEM certificate)
- `BINDU_GRPC_TLS_KEY_PATH` (PEM private key)

## Start an Agent

Example with the beginner echo agent:

```bash
python ./examples/beginner/echo_simple_agent.py
```

Expected startup logs include:

- `A2AServicer registered successfully`
- `gRPC server started on 127.0.0.1:50051`

## Verify Transport Discovery

Agent card endpoint:

```text
http://localhost:3773/.well-known/agent.json
```

You should see:

- `preferredTransport: "jsonrpc"`
- `additionalInterfaces` containing both:
  - JSON-RPC (`http://localhost`)
  - gRPC (`grpc://127.0.0.1:50051`)

Quick PowerShell check:

```powershell
Invoke-RestMethod http://localhost:3773/.well-known/agent.json | ConvertTo-Json -Depth 8
```

## gRPC Client Usage (Python)

Minimal async client example:

```python
import asyncio

from grpc import aio
from bindu.grpc import a2a_pb2, a2a_pb2_grpc


async def main() -> None:
    channel = aio.insecure_channel("127.0.0.1:50051")
    await channel.channel_ready()

    stub = a2a_pb2_grpc.A2AServiceStub(channel)

    request = a2a_pb2.MessageSendRequest(
        message=a2a_pb2.Message(
            message_id="11111111-1111-1111-1111-111111111111",
            context_id="22222222-2222-2222-2222-222222222222",
            task_id="33333333-3333-3333-3333-333333333333",
            role="user",
            kind="message",
            parts=[
                a2a_pb2.Part(
                    text=a2a_pb2.TextPart(text="Hello from gRPC client")
                )
            ],
        )
    )

    response = await stub.SendMessage(request)
    print(response.task.id)

    await channel.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## Implemented gRPC RPC Methods

Current `A2AService` methods exposed by Bindu:

- `SendMessage`
- `StreamMessage`
- `GetTask`
- `ListTasks`
- `CancelTask`
- `TaskFeedback`
- `ListContexts`
- `ClearContext`
- `SetTaskPushNotification`
- `GetTaskPushNotification`
- `ListTaskPushNotifications`
- `DeleteTaskPushNotification`
- `HealthCheck`

These methods are integrated with the same task lifecycle and storage/scheduler backends used by JSON-RPC.

## Authentication for gRPC (Optional)

If auth is enabled, gRPC requests require `authorization` metadata with a bearer token.

Auth is validated via the repo’s Hydra auth flow (`HYDRA__*` + `AUTH__*` settings).

Client metadata example:

```python
response = await stub.SendMessage(
    request,
    metadata=(("authorization", "Bearer <ACCESS_TOKEN>"),),
)
```

Without a valid token (when auth is enabled), the server returns `UNAUTHENTICATED`.

## TLS for gRPC (Optional)

Enable TLS:

```bash
BINDU_GRPC_TLS_ENABLED=true
BINDU_GRPC_TLS_CERT_PATH=/path/to/server.crt
BINDU_GRPC_TLS_KEY_PATH=/path/to/server.key
```

When TLS is enabled, both cert and key paths are required.

## Troubleshooting

- `/.well-known/agent.json` returns 500
  - Restart the agent after code/config changes.
- gRPC server does not start
  - Check `BINDU_GRPC_ENABLED=true` and port availability.
- `Could not register servicer - protobuf code not generated`
  - Run `python scripts/generate_proto.py`.
- `UNAUTHENTICATED` gRPC calls
  - Verify Hydra/auth settings and bearer token metadata.

## Related Docs

- `docs/AUTHENTICATION.md`
- `docs/NOTIFICATIONS.md`
- `docs/OBSERVABILITY.md`
