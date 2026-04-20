# Building SDKs for New Languages

You want to add Bindu support for Rust, Go, Swift, or another language. Here's what's involved.

## What an SDK Does

An SDK is a thin wrapper — typically 200-400 lines — that hides gRPC from the developer. From their perspective, they call `bindufy(config, handler)` and get a microservice. The SDK handles everything in between.

Concretely, an SDK does four things:

1. **Implements `AgentHandler`** — a gRPC server that receives `HandleMessages` calls from the core and invokes the developer's handler
2. **Calls `BinduService.RegisterAgent`** — a gRPC client that registers the agent with the core
3. **Launches the Python core** — spawns `bindu serve --grpc` as a child process
4. **Exposes `bindufy(config, handler)`** — the developer-facing API that orchestrates all of the above

The proto contract at `proto/agent_handler.proto` is the single source of truth. As long as your SDK speaks the same proto, it works with any version of the core.

## Step 1: Generate gRPC Stubs

Every language has a protoc plugin. Generate client and server stubs from the proto:

| Language | Tool | Command |
|----------|------|---------|
| Rust | `tonic-build` | Add `tonic-build` to `build.rs`, it compiles the proto at build time |
| Go | `protoc-gen-go-grpc` | `protoc --go_out=. --go-grpc_out=. proto/agent_handler.proto` |
| Swift | `grpc-swift` | `protoc --swift_out=. --grpc-swift_out=. proto/agent_handler.proto` |
| C# | `Grpc.Tools` | NuGet package auto-generates from `.proto` in the project |

The generated code gives you typed message classes and service interfaces.

## Step 2: Implement AgentHandler (Server)

The core calls three methods on your SDK. You need to implement them:

**HandleMessages** — the critical one. Receives conversation history, calls the developer's handler, returns the response.

```
Input:  HandleRequest { messages: [ChatMessage{role, content}, ...] }
Output: HandleResponse { content: string, state: string, prompt: string, is_final: bool }
```

Rules:
- If the handler returns a plain string, set `content` to the string and leave `state` empty
- If the handler returns a state transition, set `state` to `"input-required"` or `"auth-required"` and `prompt` to the follow-up question
- If the handler throws, return a gRPC `INTERNAL` error with the error message
- Always set `is_final` to `true` (streaming not yet supported)

**GetCapabilities** — return static info about the SDK.

```
Output: GetCapabilitiesResponse { name, description, version, supports_streaming }
```

**HealthCheck** — return `{healthy: true, message: "OK"}`.

## Step 3: Implement BinduService Client

Your SDK needs to call two methods on the core:

**RegisterAgent** — sends config, skills, and the SDK's callback address.

```
Input: RegisterAgentRequest {
  config_json: string,       // Full config as JSON
  skills: [SkillDefinition], // Skills with raw file content
  grpc_callback_address: string  // e.g., "localhost:50052"
}
Output: RegisterAgentResponse { success, agent_id, did, agent_url, error }
```

The `config_json` is a JSON string matching the Python `bindufy()` config format. This is intentional — the config schema lives in one place (Python), and SDKs just serialize to JSON.

**Heartbeat** — call every 30 seconds to signal liveness.

```
Input: HeartbeatRequest { agent_id, timestamp }
```

## Step 4: Implement Core Launcher

The SDK needs to start the Python core as a child process. The logic:

1. Check if `bindu` CLI is available (pip-installed)
2. If not, check if `uv` is available
3. If not, fall back to `python3 -m bindu.cli`
4. Spawn: `<command> serve --grpc --grpc-port 3774`
5. Wait for `:3774` to accept TCP connections (poll every 500ms, timeout 30s)
6. On parent exit (Ctrl+C), kill the child process

## Step 5: Implement `bindufy()`

Wire everything together in a single function:

```
function bindufy(config, handler):
    skills = read_skill_files(config.skills)
    callback_port = start_agent_handler_server(handler)
    launch_python_core(grpc_port=3774)
    wait_for_port(3774)
    result = register_agent(config, skills, callback_address="localhost:{callback_port}")
    start_heartbeat_loop(result.agent_id)
    print("Agent registered! A2A URL: {result.agent_url}")
```

That's the entire SDK. Everything else is type definitions and error handling.

## Skill Loading

Skills are files in the developer's project. The SDK reads them and sends the content in the `RegisterAgent` call:

1. For each skill path in `config.skills`, look for `skill.yaml` or `SKILL.md`
2. Read the file content
3. Parse the name and description (from YAML frontmatter or YAML fields)
4. Send as `SkillDefinition { name, description, tags, raw_content, format }`

The core processes the skill content without needing filesystem access to the SDK's project.

## Testing Your SDK

**Unit test:** Mock the gRPC channel and verify `HandleMessages` correctly invokes the handler and serializes the response.

**Integration test:** Start a real Bindu core with `bindu serve --grpc`, register an agent from your SDK, send an A2A message, and verify the response. The Python E2E tests in `tests/integration/grpc/test_grpc_e2e.py` show exactly this pattern.

**Smoke test:** Run one of the examples end-to-end and `curl` the agent.

## Reference: TypeScript SDK

The TypeScript SDK at `sdks/typescript/` is the reference implementation. Study these files:

| File | What it does | Lines |
|------|-------------|-------|
| `src/index.ts` | `bindufy()` function + skill loader | ~220 |
| `src/server.ts` | AgentHandler gRPC server | ~130 |
| `src/client.ts` | BinduService gRPC client | ~105 |
| `src/core-launcher.ts` | Spawns Python core | ~170 |
| `src/types.ts` | TypeScript interfaces | ~120 |

Total: ~745 lines. That's the entire SDK. Most of that is type definitions and error handling. The core logic is under 300 lines.

## Publishing

Publish to your language's package registry:

| Language | Registry | Package name convention |
|----------|----------|----------------------|
| Rust | crates.io | `bindu-sdk` |
| Go | Go modules | `github.com/getbindu/bindu-sdk-go` |
| Swift | Swift Package Manager | `bindu-sdk` |
| C# | NuGet | `Bindu.Sdk` |

Include the proto file in the package so users don't need to download it separately.
