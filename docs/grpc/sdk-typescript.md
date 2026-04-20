# TypeScript SDK

## The Idea

You have a TypeScript agent. Maybe it uses the OpenAI SDK, LangChain.js, or just raw `fetch` calls. You want it to be a real microservice — with identity, authentication, payments, and a standard protocol. But you don't want to rewrite infrastructure.

```typescript
import { bindufy } from "@bindu/sdk";

bindufy({
  author: "dev@example.com",
  name: "my-agent",
  deployment: { url: "http://localhost:3773", expose: true },
}, async (messages) => {
  // Your agent logic — any framework, any LLM
  return "Hello from TypeScript!";
});
```

One function call. One terminal. Full microservice.

## Installation

```bash
npm install @bindu/sdk
```

The SDK also needs the Bindu Python core installed on the machine:

```bash
pip install bindu
```

The SDK finds and launches the Python core automatically. You don't start it manually.

## What Happens When You Call `bindufy()`

1. SDK reads your skill files (yaml/markdown) from disk
2. SDK starts a gRPC server on a random port — this is where the core will call your handler
3. SDK spawns `bindu serve --grpc` as a child process
4. SDK waits for the core's gRPC server to be ready on `:3774`
5. SDK calls `RegisterAgent` with your config, skills, and callback address
6. Core runs the full bindufy pipeline — DID, auth, x402, manifest, HTTP server
7. SDK receives the agent ID, DID, and A2A URL
8. SDK starts a heartbeat loop (every 30 seconds)
9. You see "Waiting for messages..."

When a message arrives via A2A HTTP, the core calls your handler over gRPC. You process it, return a string, and the core sends it back to the client with a DID signature.

When you press `Ctrl+C`, the SDK kills the Python core and exits.

## Handler Patterns

### Simple response

```typescript
async (messages) => {
  return "The answer is 42.";
}
```

Task completes immediately with this response.

### OpenAI SDK

```typescript
import OpenAI from "openai";
const openai = new OpenAI();

async (messages) => {
  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: messages.map(m => ({
      role: m.role as "user" | "assistant" | "system",
      content: m.content,
    })),
  });
  return response.choices[0].message.content || "";
}
```

### LangChain.js

```typescript
import { ChatOpenAI } from "@langchain/openai";
const llm = new ChatOpenAI({ model: "gpt-4o" });

async (messages) => {
  const response = await llm.invoke(
    messages.map(m => ({ role: m.role, content: m.content }))
  );
  return typeof response.content === "string"
    ? response.content
    : JSON.stringify(response.content);
}
```

### Multi-turn conversation

Sometimes your agent needs more information before it can answer. Return a state transition:

```typescript
async (messages) => {
  if (messages.length === 1) {
    // First message — ask for clarification
    return {
      state: "input-required",
      prompt: "Could you be more specific about what you're looking for?"
    };
  }

  // Second message — now answer
  const lastMessage = messages[messages.length - 1].content;
  return `Based on your clarification: here's the detailed answer about "${lastMessage}"...`;
}
```

The task stays open after `input-required`. The user sends a follow-up. The core calls your handler again with the full conversation history.

### Error handling

If your handler throws, the SDK catches it and returns a gRPC error. ManifestWorker marks the task as failed. The user gets an error response.

```typescript
async (messages) => {
  try {
    return await myLlmCall(messages);
  } catch (err) {
    // Option A: Let it throw — task fails with error message
    throw err;

    // Option B: Return a graceful message
    return "Sorry, I'm having trouble processing your request right now.";
  }
}
```

## Configuration

```typescript
bindufy({
  // Required
  author: "dev@example.com",        // Used for DID generation
  name: "my-agent",                  // Agent name
  deployment: {
    url: "http://localhost:3773",    // A2A HTTP server address
    expose: true,                    // Enable CORS
    cors_origins: ["http://localhost:5173"],
  },

  // Optional
  description: "What my agent does",
  version: "1.0.0",
  skills: ["skills/question-answering"],
  execution_cost: {                  // x402 payments
    amount: "1000000",
    token: "USDC",
    network: "base-sepolia",
  },
  capabilities: {
    streaming: false,
    push_notifications: false,
  },

  // Advanced
  coreAddress: "localhost:3774",     // Override core gRPC address
  callbackPort: 0,                   // 0 = auto-assign
  debug_mode: false,
  telemetry: true,
  num_history_sessions: 10,
}, handler);
```

## Skills

Define what your agent can do. Two options:

**File-based** (recommended) — create `skills/my-skill/skill.yaml` or `skills/my-skill/SKILL.md`:

```typescript
bindufy({
  skills: ["skills/question-answering", "skills/code-review"],
}, handler);
```

The SDK reads the files and sends the content to the core during registration.

**Inline** — define skills directly in code:

```typescript
bindufy({
  skills: [{
    name: "question-answering",
    description: "Answer questions using GPT-4o",
    tags: ["qa", "assistant"],
  }],
}, handler);
```

## Types

The SDK exports these types for your handler:

```typescript
interface ChatMessage {
  role: string;     // "user", "assistant", or "system"
  content: string;
}

// Your handler signature
type MessageHandler = (messages: ChatMessage[]) => Promise<string | HandlerResponse>;

interface HandlerResponse {
  content?: string;
  state?: "input-required" | "auth-required";
  prompt?: string;
  metadata?: Record<string, string>;
}

// Returned by bindufy()
interface RegistrationResult {
  agentId: string;
  did: string;
  agentUrl: string;
}
```

## Debugging

**Check core logs:** The Python core's output is prefixed with `[bindu-core]` in your terminal:

```
[bindu-core] INFO  gRPC server started on 0.0.0.0:3774
[bindu-core] INFO  Agent registered: openai-assistant-agent
[bindu-core] INFO  HTTP server started on 0.0.0.0:3773
```

**Test the agent manually:**

```bash
# Is the A2A server running?
curl http://localhost:3773/health

# What does the agent card look like?
curl http://localhost:3773/.well-known/agent.json | python3 -m json.tool

# Send a test message
curl -X POST http://localhost:3773 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"Hello"}],"messageId":"test-1","contextId":"test-2","taskId":"test-3","kind":"message"}},"id":"1"}'
```

**Port conflicts:**

```bash
lsof -ti:3773 -ti:3774 | xargs kill 2>/dev/null
```

## Limitations

- **No streaming** — handler must return complete responses, can't yield chunks
- **Requires Python** — the Bindu core must be installed (`pip install bindu`)
- **Single agent per port** — each `bindufy()` call uses `:3773` for HTTP

See [full limitations](./limitations.md) for details.

## Examples

- [OpenAI Agent](../../examples/typescript-openai-agent/) — direct OpenAI SDK usage
- [LangChain Agent](../../examples/typescript-langchain-agent/) — LangChain.js with ChatOpenAI
