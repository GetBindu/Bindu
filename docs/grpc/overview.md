# Architecture

## The Big Picture

A TypeScript developer writes an agent. They call `bindufy()`. Here's what happens:

```
Their TypeScript code                    Bindu Core (Python, auto-started)
┌─────────────────────┐                  ┌────────────────────────────┐
│                     │                  │                            │
│  OpenAI SDK         │  1. Register     │  Config validation         │
│  LangChain          │ ──────gRPC────►  │  DID key generation        │
│  Any framework      │                  │  Auth (Hydra OAuth2)       │
│                     │                  │  x402 payment setup        │
│  handler(messages)  │  2. Execute      │  Manifest creation         │
│  ◄──────gRPC────────│──────────────    │  Scheduler + Storage       │
│                     │                  │  HTTP/A2A server (:3773)   │
└─────────────────────┘                  └────────────────────────────┘
        SDK process                              Core process
     (developer's language)                   (Python, invisible)
```

Two processes. One terminal. The developer only sees their code. The Python process is a hidden child process that the SDK manages automatically.

## Why Two Processes?

**Because the alternative is worse.**

Option A: Rewrite Bindu's core in every language. DID, auth, x402, scheduler, storage, A2A protocol — in TypeScript, then Kotlin, then Rust. Thousands of lines, each time. Every bug fixed three times.

Option B: Keep one core. Connect to it over a wire. The handler runs in the developer's language. Everything else runs in Python. One codebase for infrastructure. Thin SDKs for each language.

We chose B. The wire is gRPC.

## Two Services, Two Directions

gRPC isn't one-way. Both sides are servers AND clients:

**BinduService** — lives in the Python core on `:3774`

The SDK calls this to register and manage its agent:

| Method | What it does |
|--------|-------------|
| `RegisterAgent` | "Here's my config, skills, and callback address. Make me a microservice." |
| `Heartbeat` | "I'm still alive." (every 30 seconds) |
| `UnregisterAgent` | "I'm shutting down. Clean up." |

**AgentHandler** — lives in the SDK on a dynamic port

The core calls this when work arrives:

| Method | What it does |
|--------|-------------|
| `HandleMessages` | "A user sent this message. Run your handler and give me the response." |
| `GetCapabilities` | "What can you do?" |
| `HealthCheck` | "Are you still there?" |

This bidirectional design is why gRPC was chosen over REST. Both sides initiate calls. REST can't do that without polling or websockets.

## Message Flow: What Happens When a User Sends a Message

A user sends "What is the capital of France?" to a TypeScript agent that's been bindufied:

```
1. User sends HTTP POST to :3773
   {"method": "message/send", "params": {"message": {"text": "What is the capital of France?"}}}

2. Bindu Core receives the request
   TaskManager creates a task, Scheduler queues it

3. ManifestWorker picks up the task
   Builds conversation history from storage
   Calls manifest.run(messages)

4. manifest.run is a GrpcAgentClient
   Converts messages to protobuf
   Calls HandleMessages on the SDK's gRPC server

5. TypeScript SDK receives the call
   Deserializes messages: [{role: "user", content: "What is the capital of France?"}]
   Calls the developer's handler function

6. Developer's handler runs
   const response = await openai.chat.completions.create({model: "gpt-4o", messages})
   Returns "The capital of France is Paris."

7. SDK sends the response back over gRPC
   HandleResponse {content: "The capital of France is Paris."}

8. GrpcAgentClient receives the response
   Returns the string to ManifestWorker

9. ManifestWorker processes the result
   ResultProcessor normalizes it
   ResponseDetector determines task state → "completed"
   ArtifactBuilder creates a DID-signed artifact

10. Core sends the A2A response back to the user
    Task completed, with DID signature on the artifact
```

The entire round trip: ~2-5 seconds. The gRPC overhead is ~1-5ms. The rest is the LLM call.

## GrpcAgentClient: The Invisible Bridge

This is the component that makes everything work. It's a Python class that pretends to be a handler function.

In `ManifestWorker`, line 171:

```python
raw_results = self.manifest.run(message_history or [])
```

For a Python agent, `manifest.run` is a local function. For a gRPC agent, it's a `GrpcAgentClient` instance. The worker can't tell the difference. It calls it the same way, gets the same types back, and processes the result identically.

This is why we didn't change ManifestWorker, ResultProcessor, ResponseDetector, or any downstream code. The abstraction holds. A callable is a callable.

## What the SDK Does When You Call `bindufy()`

Step by step, from the developer typing `npx tsx index.ts` to seeing "Waiting for messages...":

1. **SDK reads skill files** from the project directory (yaml or markdown)
2. **SDK starts an AgentHandler gRPC server** on a random available port
3. **SDK detects how to run Python** — checks for `bindu` CLI, `uv`, or `python3`
4. **SDK spawns the Bindu core** as a child process: `bindu serve --grpc --grpc-port 3774`
5. **SDK waits for `:3774` to be ready** (polls with TCP connect, 30s timeout)
6. **SDK calls `RegisterAgent`** with config JSON, skill data, and its callback address
7. **Core validates config**, generates agent ID, creates DID keys, sets up x402/auth
8. **Core creates manifest** with `manifest.run = GrpcAgentClient(callback_address)`
9. **Core starts uvicorn** on `:3773` in a background thread
10. **Core returns** `{agent_id, did, agent_url}` to the SDK
11. **SDK starts a heartbeat loop** — pings the core every 30 seconds
12. **SDK prints** "Agent registered!" and waits for HandleMessages calls

When the developer presses `Ctrl+C`, the SDK kills the Python child process and exits cleanly.

## Python vs gRPC Agents: What's Different?

| | Python Agent | gRPC Agent |
|---|---|---|
| **Developer calls** | `bindufy(config, handler)` | `bindufy(config, handler)` (identical) |
| **Handler runs in** | Same process as core | Separate process |
| **Core started by** | `bindufy()` directly | SDK spawns as child process |
| **Communication** | In-process function call | gRPC over localhost |
| **Latency overhead** | 0ms | 1-5ms |
| **Language** | Python only | Any language with gRPC |
| **DID, auth, x402** | Full support | Full support (identical) |
| **Skills** | Loaded from filesystem | Sent as data during registration |
| **Streaming** | Supported | Not yet implemented |

The key insight: from the outside (A2A clients, other agents, the frontend), there is **no visible difference**. The agent card looks the same. The DID is generated the same way. The A2A responses have the same structure. The artifacts carry the same DID signatures. A client cannot tell whether the agent behind `:3773` is Python, TypeScript, or Kotlin.
