# API Reference

The complete gRPC contract between SDKs and the Bindu core. Defined in `proto/agent_handler.proto`.

## Services

### BinduService (port 3774)

Lives in the Bindu core. SDKs call this to register and manage agents.

#### `RegisterAgent`

The main entry point. SDK sends config + skills, core runs the full bindufy pipeline and returns the agent's identity.

**Request:**
```protobuf
message RegisterAgentRequest {
  string config_json = 1;             // Full config as JSON string
  repeated SkillDefinition skills = 2; // Skills with file content
  string grpc_callback_address = 3;   // SDK's AgentHandler address
}
```

`config_json` matches the Python `bindufy()` config format:
```json
{
  "author": "dev@example.com",
  "name": "my-agent",
  "description": "What it does",
  "deployment": {"url": "http://localhost:3773", "expose": true},
  "execution_cost": {"amount": "1000000", "token": "USDC"}
}
```

**Response:**
```protobuf
message RegisterAgentResponse {
  bool success = 1;
  string agent_id = 2;   // Generated UUID
  string did = 3;         // "did:bindu:author:name:id"
  string agent_url = 4;   // "http://localhost:3773"
  string error = 5;       // Error message if success=false
}
```

**What the core does:** validates config, generates agent ID (SHA256 of author+name), creates Ed25519 DID keys, sets up x402 payments, creates manifest with `GrpcAgentClient` as handler, starts HTTP/A2A server on the configured URL.

#### `Heartbeat`

Keep-alive signal. SDKs send this every 30 seconds.

**Request:**
```protobuf
message HeartbeatRequest {
  string agent_id = 1;
  int64 timestamp = 2;   // Unix timestamp in milliseconds
}
```

**Response:**
```protobuf
message HeartbeatResponse {
  bool acknowledged = 1;      // true if agent_id is registered
  int64 server_timestamp = 2;
}
```

#### `UnregisterAgent`

Clean shutdown. SDK calls this before exiting.

**Request/Response:**
```protobuf
message UnregisterAgentRequest { string agent_id = 1; }
message UnregisterAgentResponse { bool success = 1; string error = 2; }
```

---

### AgentHandler (dynamic port)

Lives in the SDK. The core calls this when work arrives.

#### `HandleMessages`

The core sends conversation history, the SDK runs the developer's handler and returns the response.

**Request:**
```protobuf
message HandleRequest {
  repeated ChatMessage messages = 1;  // Conversation history
  string task_id = 2;
  string context_id = 3;
}

message ChatMessage {
  string role = 1;     // "user", "assistant", or "system"
  string content = 2;
}
```

**Response:**
```protobuf
message HandleResponse {
  string content = 1;                  // The response text
  string state = 2;                    // "" = completed, "input-required", "auth-required"
  string prompt = 3;                   // Follow-up prompt (when state is set)
  bool is_final = 4;                   // Always true (streaming not implemented)
  map<string, string> metadata = 5;
}
```

**Response rules:**
- **Normal response:** `{content: "answer", state: ""}` -> task completes
- **Need more info:** `{state: "input-required", prompt: "Can you clarify?"}` -> task stays open
- **Need auth:** `{state: "auth-required"}` -> task stays open
- **Error:** Return gRPC `INTERNAL` status -> task fails

#### `HandleMessagesStream`

Server-side streaming variant. **Defined in proto but not implemented** in `GrpcAgentClient`. See [limitations](./limitations.md).

#### `GetCapabilities`

Core queries what the SDK agent supports.

**Response:**
```protobuf
message GetCapabilitiesResponse {
  string name = 1;
  string description = 2;
  string version = 3;
  bool supports_streaming = 4;
  repeated SkillDefinition skills = 5;
}
```

#### `HealthCheck`

Core verifies the SDK is responsive.

**Response:**
```protobuf
message HealthCheckResponse {
  bool healthy = 1;
  string message = 2;   // "OK" or diagnostic info
}
```

---

## Shared Message Types

#### `SkillDefinition`

Sent during registration. Carries the skill file content so the core doesn't need filesystem access.

```protobuf
message SkillDefinition {
  string name = 1;
  string description = 2;
  repeated string tags = 3;
  repeated string input_modes = 4;
  repeated string output_modes = 5;
  string version = 6;
  string author = 7;
  string raw_content = 8;   // Full skill.yaml or SKILL.md content
  string format = 9;        // "yaml" or "markdown"
}
```

---

## Configuration

Environment variables for the gRPC server:

| Variable | Default | Description |
|----------|---------|-------------|
| `GRPC__ENABLED` | `false` | Enable gRPC server |
| `GRPC__HOST` | `0.0.0.0` | Bind address |
| `GRPC__PORT` | `3774` | Server port |
| `GRPC__MAX_WORKERS` | `10` | Thread pool size |
| `GRPC__MAX_MESSAGE_LENGTH` | `4194304` | Max message size (4MB) |
| `GRPC__HANDLER_TIMEOUT` | `30.0` | HandleMessages timeout (seconds) |
| `GRPC__HEALTH_CHECK_INTERVAL` | `30` | Health check interval (seconds) |

---

## Testing with grpcurl

```bash
# List services
grpcurl -plaintext -import-path proto -proto agent_handler.proto localhost:3774 list

# Heartbeat
grpcurl -plaintext -emit-defaults \
  -proto proto/agent_handler.proto -import-path proto \
  -d '{"agent_id": "test", "timestamp": 1711234567890}' \
  localhost:3774 bindu.grpc.BinduService.Heartbeat

# RegisterAgent
grpcurl -plaintext -emit-defaults \
  -proto proto/agent_handler.proto -import-path proto \
  -d '{"config_json": "{\"author\":\"test@example.com\",\"name\":\"test\",\"deployment\":{\"url\":\"http://localhost:3773\",\"expose\":true}}", "skills": [], "grpc_callback_address": "localhost:50052"}' \
  localhost:3774 bindu.grpc.BinduService.RegisterAgent
```
