# TypeScript OpenAI Agent

A general-purpose assistant built with the [OpenAI SDK](https://github.com/openai/openai-node) and bindufied using the [Bindu TypeScript SDK](../../sdks/typescript/). One `bindufy()` call transforms the OpenAI agent into a full A2A-compliant microservice with DID identity, authentication, x402 payments, and task scheduling.

## What This Example Demonstrates

- Writing an agent in TypeScript using the OpenAI SDK
- Calling `bindufy()` to convert it into a networked microservice
- The Bindu core (Python) starts automatically in the background
- The agent registers over gRPC and receives task execution calls
- External clients interact via standard A2A HTTP protocol

## Architecture

```
Developer runs: npx tsx index.ts

  TypeScript Process                     Python Process (auto-started)
  ┌─────────────────────┐               ┌──────────────────────────────┐
  │  OpenAI SDK          │               │  Bindu Core                  │
  │  handler(messages)   │◄── gRPC ────►│  DID, Auth, x402, A2A       │
  │                      │  :50052       │  Scheduler, Storage          │
  │  @bindu/sdk          │               │  HTTP Server :3773           │
  └─────────────────────┘               └──────────────────────────────┘
                                                    ▲
                                                    │ A2A Protocol
                                                    │ (HTTP/JSON-RPC)
                                               External Clients
```

## Prerequisites

- **Node.js** >= 18
- **Python** >= 3.12 with Bindu installed:
  ```bash
  pip install bindu
  # or with uv:
  uv pip install bindu
  ```
- **OpenAI API key** from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Setup

### 1. Clone and navigate

```bash
cd examples/typescript-openai-agent
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-openai-api-key
```

Optionally set a different model:

```env
OPENAI_MODEL=gpt-4o-mini
```

### 3. Install dependencies

```bash
npm install
```

This installs:
- `@bindu/sdk` — the Bindu TypeScript SDK (linked from `../../sdks/typescript`)
- `openai` — the OpenAI Node.js SDK
- `dotenv` — loads `.env` variables

## Run

```bash
npm start
# or directly:
npx tsx index.ts
```

You should see output like:

```
[Bindu SDK] Starting Bindu core...
[Bindu SDK] Bindu core is ready on :3774
[Bindu SDK] AgentHandler gRPC server started on :50052
[Bindu SDK] Registering agent with Bindu core...
[Bindu SDK]
[Bindu SDK] Agent registered successfully!
[Bindu SDK]   Agent ID:  91547067-c183-e0fd-c150-27a3ca4135ed
[Bindu SDK]   DID:       did:bindu:opnai_sample_ts_at_getbindu_com:openai-assistant-agent:91547067...
[Bindu SDK]   A2A URL:   http://localhost:3773
[Bindu SDK]
[Bindu SDK] Waiting for messages...
```

**What happened behind the scenes:**
1. The SDK started the Python Bindu core as a child process
2. The core started a gRPC server on `:3774`
3. The SDK started an AgentHandler gRPC server on `:50052`
4. The SDK called `RegisterAgent` on the core with your config
5. The core ran the full bindufy logic: generated DID, set up auth, created manifest
6. The core started an HTTP/A2A server on `:3773`
7. The agent is now a fully functional A2A microservice

## Test the Agent

### Send a message

Open a **new terminal** and run:

```bash
curl -s -X POST http://localhost:3773 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What is the capital of France?"}],
        "messageId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "contextId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "taskId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "kind": "message"
      },
      "configuration": {
        "acceptedOutputModes": ["text/plain"],
        "blocking": true
      }
    },
    "id": "test-1"
  }' | python3 -m json.tool
```

### Get the completed task

Wait a few seconds for GPT-4o to respond, then:

```bash
curl -s -X POST http://localhost:3773 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {
      "taskId": "c3d4e5f6-a7b8-9012-cdef-123456789012"
    },
    "id": "test-2"
  }' | python3 -m json.tool
```

You should see GPT-4o's answer in the task history.

### Check the agent card

```bash
curl -s http://localhost:3773/.well-known/agent.json | python3 -m json.tool
```

This returns the full A2A agent card with DID, skills, and capabilities.

### Check health

```bash
curl -s http://localhost:3773/health
```

## How the Code Works

```typescript
import { bindufy, ChatMessage } from "@bindu/sdk";
import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

bindufy(
  {
    author: "opnai-sample-ts@getbindu.com",    // Your identity
    name: "openai-assistant-agent",              // Agent name
    description: "An assistant powered by GPT-4o",
    deployment: {
      url: "http://localhost:3773",              // A2A HTTP server URL
      expose: true,
    },
    skills: ["skills/question-answering"],        // Skill definitions
  },
  async (messages: ChatMessage[]) => {
    // This handler is called every time a message arrives via A2A.
    // messages = [{role: "user", content: "..."}, ...]
    // Return a string for normal responses.
    // Return {state: "input-required", prompt: "..."} for multi-turn.

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

## Message Flow

```
1. Client sends A2A HTTP POST to :3773
2. Bindu Core receives request
3. TaskManager creates task, Scheduler queues it
4. Worker picks up task, builds message history
5. Worker calls manifest.run(messages)
   └── This is GrpcAgentClient — makes gRPC call to TypeScript process
6. TypeScript SDK receives HandleMessages on :50052
7. SDK calls your handler(messages) — the async function above
8. Your handler calls OpenAI GPT-4o API
9. OpenAI returns response
10. SDK sends response back over gRPC
11. Worker processes result (ResultProcessor, ResponseDetector)
12. Worker updates storage, creates artifacts with DID signature
13. Client receives A2A JSON-RPC response
```

## Project Structure

```
typescript-openai-agent/
  index.ts                    # Agent code — OpenAI SDK + bindufy()
  package.json                # Dependencies (@bindu/sdk, openai, dotenv)
  tsconfig.json               # TypeScript configuration
  .env.example                # Environment variable template
  .env                        # Your actual keys (git-ignored)
  README.md                   # This file
  skills/
    question-answering/
      skill.yaml              # Skill definition (YAML format)
      SKILL.md                # Skill documentation (Markdown format)
```

## Ports Used

| Port | Protocol | Purpose |
|------|----------|---------|
| 3773 | HTTP | A2A server (external clients connect here) |
| 3774 | gRPC | Bindu core registration (SDK connects here) |
| 50052 | gRPC | AgentHandler (core calls SDK handler here) |

## Troubleshooting

### "Bindu not found"

Install the Python package:

```bash
pip install bindu[grpc]
```

### "Port 3773 already in use"

Kill existing processes:

```bash
lsof -ti:3773 -ti:3774 | xargs kill 2>/dev/null
```

### "OPENAI_API_KEY not set"

Make sure your `.env` file exists and has a valid key:

```bash
cat .env
# Should show: OPENAI_API_KEY=sk-...
```

### Agent starts but no response to messages

Check the first terminal for error logs. Common issues:
- Invalid API key
- Model not available on your OpenAI plan
- Rate limiting

## Stop the Agent

Press `Ctrl+C` in the terminal. This kills both the TypeScript process and the Python core.

## Next Steps

- Try the [TypeScript LangChain Agent](../typescript-langchain-agent/) for a framework-based example
- Read the [gRPC Documentation](../../docs/GRPC_LANGUAGE_AGNOSTIC.md) for architecture details
- Build your own agent: copy this folder, change the handler, run `bindufy()`
