---
name: debug-grpc-connection
description: Diagnose gRPC connection issues between the Bindu core and a language SDK. Use when an SDK fails to register, HandleMessages calls time out, "connection refused" on :3774, heartbeats stop arriving, or the core logs "agent silently died".
---

# Debug gRPC Connection

## Overview

The Bindu core (Python) runs a gRPC server on port `3774` that SDKs connect to via `RegisterAgent` and `Heartbeat`. After registration, the core calls back into the SDK's own gRPC server (ephemeral port) via `HandleMessages`. Most connection bugs are in that handshake.

See [docs/grpc/overview.md](../../../docs/grpc/overview.md) for the full message flow and [docs/grpc/limitations.md](../../../docs/grpc/limitations.md) for known unimplemented behaviors.

## Inputs

- Which end is reporting the failure: core logs vs. SDK logs.
- The exact error message and/or symptom.
- Recent commits touching `proto/`, `bindu/grpc/`, or `sdks/typescript/src/`.

## Safety

- Do not modify files under `bindu/grpc/generated/` or `sdks/typescript/src/generated/` to "make the error go away". Proto drift is the underlying problem — fix it with the `regenerate-grpc-stubs` skill.
- Do not bypass the heartbeat mechanism. The core relies on heartbeats to clean up dead-agent registrations.
- Do not assume the SDK is at fault before inspecting core logs — the core is the ground truth for registration state.

## Execution Contract

1. Confirm both processes are alive and bound to expected ports.
2. Inspect core logs for the registration handshake.
3. Probe the core directly with `grpcurl`.
4. Check for proto drift.
5. Verify SDK heartbeat timing.
6. Consult limitations doc before filing a bug.

## Steps

### 1. Confirm both processes and ports

```bash
lsof -ti:3773 -ti:3774
ps aux | grep -E '(bindu|node.*agent|python.*bindu)' | grep -v grep
```

- `3773` missing → HTTP/A2A server never started. Check for port clash (`lsof -i:3773`).
- `3774` missing → core started without `--grpc`. Restart with `bindu serve --grpc`.
- SDK process missing → it crashed. Check its own logs for a stacktrace.

### 2. Inspect core logs

Filter for the `[bindu-core]` prefix. Meaningful signals:

| Log line | Means |
| --- | --- |
| `grpc server listening on 0.0.0.0:3774` | Core gRPC up, accepting connections |
| `agent registered: <did>` | SDK successfully called `RegisterAgent` |
| `heartbeat received from <did>` | SDK is alive and connected |
| `agent silently died: <did>` | No heartbeat in >90s; registration pruned |
| `failed to deserialize HandleMessages response` | Proto drift between core and SDK |
| `connection refused dialing <host>:<port>` | Core can't reach back into SDK's gRPC server |

### 3. Probe the core with grpcurl

```bash
# List services — confirms the core is accepting connections
grpcurl -plaintext -proto proto/agent_handler.proto localhost:3774 list

# Synthetic heartbeat — confirms the service is bound
grpcurl -plaintext -proto proto/agent_handler.proto \
  -d '{"agent_id":"test","timestamp":1234567890}' \
  localhost:3774 bindu.grpc.BinduService.Heartbeat
```

- `list` fails with connection refused → server not bound (check step 1).
- `list` works but `Heartbeat` errors → proto mismatch or handler crash. Read the error body carefully.

### 4. Check for proto drift

```bash
# Any proto changes without matching generated-tree changes?
git log --oneline -10 -- proto/
git log --oneline -10 -- bindu/grpc/generated/ sdks/typescript/src/generated/
```

If the proto moved but the generated trees didn't — stubs are stale. Run the `regenerate-grpc-stubs` skill.

### 5. Verify SDK heartbeat timing

SDKs must send `Heartbeat` every 30 seconds after `RegisterAgent`. TypeScript SDK heartbeat logic lives in [sdks/typescript/src/client.ts](../../../sdks/typescript/src/client.ts).

Common bugs:
- Heartbeat interval never started (check the `setInterval` call).
- Heartbeat errors swallowed silently (check for try/catch around the call).
- Process exits between heartbeats (Node.js event loop starved).

### 6. Consult limitations

Before filing a bug, confirm the behavior isn't documented as known-missing in [docs/grpc/limitations.md](../../../docs/grpc/limitations.md). Things currently not implemented:

- Streaming responses (`HandleMessagesStream`)
- TLS / mTLS (localhost only is safe)
- Automatic SDK reconnection
- Connection pooling in `GrpcAgentClient`

## Never do

- **Never edit generated stubs** to silence a proto drift error. Regenerate instead.
- **Never disable heartbeats** to avoid "agent silently died" logs — that's the error reporting the real issue.
- **Never run the core without `--grpc`** and expect SDKs to work. There is no fallback path.
- **Never deploy to non-localhost without mTLS** — see [docs/MTLS_DEPLOYMENT_GUIDE.md](../../../docs/MTLS_DEPLOYMENT_GUIDE.md).
