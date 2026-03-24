# @bindu/sdk — TypeScript SDK for Bindu

Transform any TypeScript agent into a full A2A-compliant microservice with one function call.

Write your agent in any TypeScript framework — OpenAI SDK, LangChain, Vercel AI, or plain `fetch` — then call `bindufy()`. Bindu handles DID identity, authentication, x402 payments, task scheduling, storage, and the A2A protocol. You just write the handler.

## Installation

```bash
npm install @bindu/sdk
```

**Prerequisite:** The Bindu Python core must be installed on the machine:

```bash
pip install bindu
# or with uv:
uv pip install bindu
```

The SDK automatically launches the Python core as a background process — you don't need to start it manually.

## Quick Start

```typescript
import { bindufy } from "@bindu/sdk";
import OpenAI from "openai";

const openai = new OpenAI();

bindufy(
  {
    author: "dev@example.com",
    name: "my-agent",
    deployment: { url: "http://localhost:3773", expose: true },
    skills: ["skills/question-answering"],
  },
  async (messages) => {
    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: messages.map((m) => ({
        role: m.role as "user" | "assistant" | "system",
        content: m.content,
      })),
    });
    return response.choices[0].message.content || "";
  }
);
```

Run it:

```bash
npx tsx index.ts
```

That's it. Your agent is now a microservice at `http://localhost:3773` with DID, auth, and A2A protocol support.

## What `bindufy()` Does

When you call `bindufy(config, handler)`, the SDK:

1. **Launches the Bindu Python core** as a child process (gRPC on `:3774`)
2. **Starts a gRPC server** for your handler (dynamic port)
3. **Reads skill files** from your project directory
4. **Registers your agent** with the core via `RegisterAgent` gRPC call
5. **Core runs full bindufy logic**: DID key generation, auth setup, x402 payments, manifest creation
6. **Core starts HTTP/A2A server** on the configured port (`:3773`)
7. **Returns** your agent ID, DID, and A2A URL

When a message arrives via A2A HTTP, the core's worker calls your handler over gRPC. Your handler runs, returns a response, and the core sends it back to the client. You never touch gRPC, HTTP, or A2A — it's all handled internally.

```
Client ──HTTP──► Bindu Core ──gRPC──► Your Handler ──► LLM API
                 (:3773)              (:dynamic)
                 DID, Auth, x402
                 Scheduler, Storage
```

## API Reference

### `bindufy(config, handler)`

Transforms your agent into a Bindu microservice.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `BinduConfig` | Agent configuration (see below) |
| `handler` | `MessageHandler` | Your handler function |

**Returns:** `Promise<RegistrationResult>` with `agentId`, `did`, and `agentUrl`.

### `BinduConfig`

```typescript
interface BinduConfig {
  // Required
  author: string;                    // Your email (used for DID generation)
  name: string;                      // Agent name
  deployment: DeploymentConfig;      // Where to serve the agent

  // Optional
  description?: string;              // Agent description
  version?: string;                  // Default: "1.0.0"
  skills?: SkillConfig[];            // Skill file paths or inline definitions
  capabilities?: Capabilities;       // Streaming, push notifications, etc.
  kind?: "agent" | "team" | "workflow"; // Default: "agent"
  execution_cost?: ExecutionCost;    // x402 payment configuration
  coreAddress?: string;              // Core gRPC address (default: "localhost:3774")
  callbackPort?: number;             // Handler port (default: auto-assigned)
  extra_metadata?: Record<string, string>;
  debug_mode?: boolean;
  telemetry?: boolean;               // Default: true
  num_history_sessions?: number;     // Default: 10
}
```

### `DeploymentConfig`

```typescript
interface DeploymentConfig {
  url: string;                       // A2A server URL (e.g., "http://localhost:3773")
  expose?: boolean;                  // Expose to CORS origins (default: false)
  protocol_version?: string;         // A2A protocol version
  cors_origins?: string[];           // Allowed CORS origins
}
```

### `MessageHandler`

```typescript
type MessageHandler = (messages: ChatMessage[]) => Promise<string | HandlerResponse>;
```

Your handler receives the conversation history and returns either:

- **A string** — normal response, task completes
- **A `HandlerResponse` object** — for state transitions (multi-turn conversations)

### `ChatMessage`

```typescript
interface ChatMessage {
  role: string;     // "user", "assistant", or "system"
  content: string;  // Message text
}
```

### `HandlerResponse`

```typescript
interface HandlerResponse {
  content?: string;
  state?: "input-required" | "auth-required";
  prompt?: string;
  metadata?: Record<string, string>;
}
```

Return a `HandlerResponse` with `state` to keep the task open for follow-up:

```typescript
// Multi-turn: ask for clarification
return { state: "input-required", prompt: "Could you be more specific?" };

// Normal completion: just return a string
return "The capital of France is Paris.";
```

### `ExecutionCost`

```typescript
interface ExecutionCost {
  amount: string;           // Amount in atomic units
  token?: string;           // Token type (default: "USDC")
  network?: string;         // Network (default: "base-sepolia")
  pay_to_address?: string;  // Payment recipient address
}
```

### `RegistrationResult`

```typescript
interface RegistrationResult {
  agentId: string;  // Generated agent UUID
  did: string;      // DID identity (e.g., "did:bindu:...")
  agentUrl: string; // A2A HTTP URL (e.g., "http://localhost:3773")
}
```

## Skills

Skills define what your agent can do. The SDK supports two formats:

### File-based skills (recommended)

Create a `skills/` directory with YAML or Markdown skill definitions:

```
my-agent/
  index.ts
  skills/
    question-answering/
      skill.yaml       # YAML format
      SKILL.md         # Markdown format (alternative)
```

Reference them by path in your config:

```typescript
bindufy({
  skills: ["skills/question-answering"],
  // ...
}, handler);
```

The SDK reads the skill files from disk and sends the content to the core during registration.

### Inline skills

Define skills directly in code:

```typescript
bindufy({
  skills: [
    {
      name: "question-answering",
      description: "General Q&A capability",
      tags: ["qa", "assistant"],
      input_modes: ["text/plain"],
      output_modes: ["text/plain"],
    },
  ],
  // ...
}, handler);
```

## Examples

### OpenAI SDK

```typescript
import { bindufy } from "@bindu/sdk";
import OpenAI from "openai";

const openai = new OpenAI();

bindufy({
  author: "dev@example.com",
  name: "openai-agent",
  deployment: { url: "http://localhost:3773", expose: true },
}, async (messages) => {
  const res = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: messages.map((m) => ({
      role: m.role as "user" | "assistant" | "system",
      content: m.content,
    })),
  });
  return res.choices[0].message.content || "";
});
```

### LangChain

```typescript
import { bindufy } from "@bindu/sdk";
import { ChatOpenAI } from "@langchain/openai";

const llm = new ChatOpenAI({ model: "gpt-4o" });

bindufy({
  author: "dev@example.com",
  name: "langchain-agent",
  deployment: { url: "http://localhost:3773", expose: true },
}, async (messages) => {
  const res = await llm.invoke(
    messages.map((m) => ({
      role: m.role,
      content: m.content,
    }))
  );
  return typeof res.content === "string" ? res.content : JSON.stringify(res.content);
});
```

### Echo agent (no LLM)

```typescript
import { bindufy } from "@bindu/sdk";

bindufy({
  author: "dev@example.com",
  name: "echo-agent",
  deployment: { url: "http://localhost:3773", expose: true },
}, async (messages) => {
  return `Echo: ${messages[messages.length - 1].content}`;
});
```

### Multi-turn conversation

```typescript
import { bindufy } from "@bindu/sdk";

bindufy({
  author: "dev@example.com",
  name: "survey-agent",
  deployment: { url: "http://localhost:3773", expose: true },
}, async (messages) => {
  const lastMessage = messages[messages.length - 1].content;

  if (messages.length === 1) {
    // First message — ask for more info
    return { state: "input-required", prompt: "What topic would you like to explore?" };
  }

  // Follow-up — provide answer
  return `Great question about "${lastMessage}". Here's what I found...`;
});
```

### x402 Payments

```typescript
import { bindufy } from "@bindu/sdk";

bindufy({
  author: "dev@example.com",
  name: "premium-agent",
  deployment: { url: "http://localhost:3773", expose: true },
  execution_cost: {
    amount: "1000000",
    token: "USDC",
    network: "base-sepolia",
    pay_to_address: "0xYourAddress",
  },
}, async (messages) => {
  // This handler only runs after payment is verified
  return "Premium response!";
});
```

## How It Works Internally

```
bindufy(config, handler)
  |
  |  1. Detect Bindu CLI (bindu / uv run bindu / python -m bindu.cli)
  |  2. Spawn: bindu serve --grpc --grpc-port 3774
  |  3. Wait for :3774 to be ready
  |
  |  4. Start AgentHandler gRPC server on dynamic port
  |     (receives HandleMessages calls from core)
  |
  |  5. Read skill files from disk
  |  6. Call BinduService.RegisterAgent on :3774
  |     (sends config JSON + skills + callback address)
  |
  |  Core runs full bindufy logic:
  |     - Config validation
  |     - Agent ID generation (SHA256 of author+name)
  |     - DID setup (Ed25519 key generation)
  |     - x402 payment extension (if execution_cost set)
  |     - Manifest creation (manifest.run = GrpcAgentClient)
  |     - BinduApplication (Starlette + middleware)
  |     - Start uvicorn on :3773
  |
  |  7. Return {agentId, did, agentUrl}
  |  8. Start heartbeat loop (every 30s)
  |  9. Wait for HandleMessages calls
```

## Ports

| Port | Protocol | Who | Purpose |
|------|----------|-----|---------|
| 3773 | HTTP | Bindu Core | A2A protocol server (clients connect here) |
| 3774 | gRPC | Bindu Core | Registration server (SDK connects here) |
| dynamic | gRPC | SDK | Handler server (core calls SDK here) |

## Troubleshooting

### "Bindu core did not start within 30s"

The Python core failed to launch. Check:

```bash
# Is Bindu installed?
pip show bindu

# Can it run?
bindu serve --grpc --help

# Or with uv:
uv run bindu serve --grpc --help
```

### "Registration failed"

The core started but rejected the config. Check the `[bindu-core]` log lines in your terminal for error details. Common causes:
- Missing `author` or `name` in config
- Port already in use

### "Handler error" in responses

Your handler function threw an exception. The error is logged in the terminal. Common causes:
- Missing API key in `.env`
- Network error calling LLM API
- Invalid response format

### Port conflicts

```bash
lsof -ti:3773 -ti:3774 | xargs kill 2>/dev/null
```

## Project Structure

```
sdks/typescript/
  package.json                # @bindu/sdk package definition
  tsconfig.json               # TypeScript configuration
  proto/
    agent_handler.proto       # gRPC contract (copy from repo root)
  src/
    index.ts                  # Main entry — bindufy() function, skill loader
    server.ts                 # AgentHandler gRPC server (receives HandleMessages)
    client.ts                 # BinduService gRPC client (calls RegisterAgent)
    core-launcher.ts          # Spawns Python core as child process
    types.ts                  # TypeScript interfaces (ChatMessage, BinduConfig, etc.)
  dist/                       # Compiled JavaScript output
```

## Development

```bash
# Build the SDK
npm run build

# Watch mode for development
npm run dev

# Regenerate proto stubs (after changing agent_handler.proto)
npm run generate-proto
```

## License

Apache-2.0 — see [LICENSE](../../LICENSE) for details.
