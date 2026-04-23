# Language-Agnostic Agents

## The Problem

You built a great agent in TypeScript. It uses the OpenAI SDK, calls GPT-4o, handles multi-turn conversations. But to make it a **real microservice** — with identity, authentication, payments, task scheduling, and an interoperable protocol — you'd need to rewrite all of that infrastructure from scratch. In TypeScript. Again.

That's months of work. And then someone wants a Kotlin agent. Start over.

## The Solution

Bindu's gRPC adapter lets any language call `bindufy()` and get the **exact same microservice** a Python agent gets. DID identity, A2A protocol, x402 payments, OAuth2 auth, Redis scheduling, PostgreSQL storage — all of it. No reimplementation.

**Python** (direct, in-process):
```python
bindufy(config, handler)  # handler runs in the same process
```

**TypeScript** (via gRPC):
```typescript
bindufy(config, handler)  // handler runs here, infrastructure runs in Python
```

Same function name. Same config. Same result. Different language.

The gRPC layer is invisible to the developer. They never write proto files, start gRPC servers, or think about serialization. They call `bindufy()`, write a handler, and get a microservice.

## How It Actually Works

When a TypeScript developer calls `bindufy()`, three things happen:

**1. The SDK starts the Bindu core as a child process.**
The Python core handles all the infrastructure — DID, auth, x402, scheduling, storage, the HTTP server. The TypeScript developer doesn't install Python manually; the SDK detects it and spawns it.

**2. The SDK registers the agent over gRPC.**
It sends the config (author, name, skills, payment settings) to the core. The core runs the full bindufy logic — the same code path a Python agent takes — and starts an A2A HTTP server.

**3. When messages arrive, the core calls the SDK's handler over gRPC.**
A client sends an A2A message to `:3773`. The core's worker picks it up and calls `manifest.run(messages)`. For a gRPC agent, that's a `HandleMessages` call to the TypeScript process. The handler runs, returns a response, and the core sends it back to the client.

```
Client ──HTTP──► Bindu Core ──gRPC──► TypeScript Handler ──► OpenAI
         :3773   (Python)     :3774    (your code)

         DID, Auth, x402               Just the handler.
         Scheduler, Storage             That's all you write.
         A2A protocol
```

The developer writes the handler. Bindu writes everything else.

## Documentation

| Page | What you'll learn |
|------|------------------|
| [Architecture](./overview.md) | How the pieces fit together — diagrams, message flow, component breakdown |
| [API Reference](./api-reference.md) | Every gRPC method, every field, every response code |
| [GrpcAgentClient](./client.md) | How the core calls remote agents — the bridge between Python and everything else |
| [TypeScript SDK](./sdk-typescript.md) | Building TypeScript agents — installation, config, handler patterns, debugging |
| [Building New SDKs](./sdk-development.md) | Adding support for Rust, Go, Swift, or any language with gRPC |
| [Limitations](./limitations.md) | What doesn't work yet — streaming, TLS, connection pooling |

## Real Examples

- [TypeScript + OpenAI](../../examples/typescript-openai-agent/) — GPT-4o agent with one `bindufy()` call
- [TypeScript + LangChain](../../examples/typescript-langchain-agent/) — LangChain.js research assistant
- [Kotlin + OpenAI](../../examples/kotlin-openai-agent/) — Kotlin agent with the same pattern

## Quick Test

Start the gRPC server and verify it's alive:

```bash
uv run bindu serve --grpc

# In another terminal:
grpcurl -plaintext localhost:3774 list
# → bindu.grpc.AgentHandler
# → bindu.grpc.BinduService
```

Register an agent from grpcurl:

```bash
grpcurl -plaintext -emit-defaults \
  -proto proto/agent_handler.proto \
  -import-path proto \
  -d '{
    "config_json": "{\"author\":\"test@example.com\",\"name\":\"test-agent\",\"description\":\"Test\",\"deployment\":{\"url\":\"http://localhost:3773\",\"expose\":true}}",
    "skills": [],
    "grpc_callback_address": "localhost:50052"
  }' \
  localhost:3774 bindu.grpc.BinduService.RegisterAgent

# → {"success": true, "agentId": "...", "did": "did:bindu:...", "agentUrl": "http://localhost:3773"}
```

That response means the full bindufy pipeline ran: config validation, DID key generation, manifest creation, HTTP server started. Over gRPC. From the command line.

## Ports

```
:3773  HTTP   — A2A protocol (clients connect here)
:3774  gRPC   — Agent registration (SDKs connect here)
:XXXXX gRPC   — Handler execution (core calls SDKs here, dynamic port)
```
