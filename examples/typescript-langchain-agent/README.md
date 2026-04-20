# TypeScript LangChain Agent

A research assistant built with [LangChain.js](https://js.langchain.com/) and bindufied using the [Bindu TypeScript SDK](../../sdks/typescript/). One `bindufy()` call transforms the LangChain agent into a full A2A-compliant microservice with DID identity, authentication, x402 payments, and task scheduling.

## What This Example Demonstrates

- Writing an agent in TypeScript using LangChain.js (`ChatOpenAI`)
- Calling `bindufy()` to convert it into a networked microservice
- The Bindu core (Python) starts automatically in the background
- The agent registers over gRPC and receives task execution calls
- External clients interact via standard A2A HTTP protocol

## Architecture

```
Developer runs: npx tsx index.ts

  TypeScript Process                     Python Process (auto-started)
  ┌─────────────────────┐               ┌──────────────────────────────┐
  │  LangChain.js        │               │  Bindu Core                  │
  │  ChatOpenAI          │◄── gRPC ────►│  DID, Auth, x402, A2A       │
  │  handler(messages)   │  :50052       │  Scheduler, Storage          │
  │                      │               │  HTTP Server :3773           │
  │  @bindu/sdk          │               │                              │
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
cd examples/typescript-langchain-agent
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-your-openai-api-key
```

### 3. Install dependencies

```bash
npm install
```

This installs:
- `@bindu/sdk` — the Bindu TypeScript SDK (linked from `../../sdks/typescript`)
- `@langchain/openai` — LangChain.js OpenAI integration
- `dotenv` — loads `.env` variables

## Run

```bash
npm start
# or directly:
npx tsx index.ts
```

You should see output like:

```
Starting Bindu core: uv run bindu serve --grpc ...
Bindu core is ready on :3774
AgentHandler gRPC server on :50052
Registering with Bindu core...

Agent registered successfully!
  Agent ID:  ...
  DID:       did:bindu:dev_at_example_com:langchain-research-agent:...
  A2A URL:   http://localhost:3773

Waiting for messages...
```

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
        "parts": [{"kind": "text", "text": "Explain the A2A protocol in simple terms"}],
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

### Check the agent card

```bash
curl -s http://localhost:3773/.well-known/agent.json | python3 -m json.tool
```

### Check health

```bash
curl -s http://localhost:3773/health
```

## How the Code Works

```typescript
import { bindufy, ChatMessage } from "@bindu/sdk";
import { ChatOpenAI } from "@langchain/openai";

// Create LangChain model — developer's choice
const llm = new ChatOpenAI({ model: "gpt-4o", temperature: 0.7 });

bindufy(
  {
    author: "dev@example.com",
    name: "langchain-research-agent",
    description: "A research assistant built with LangChain.js",
    deployment: { url: "http://localhost:3773", expose: true },
    skills: ["skills/research"],
  },
  async (messages: ChatMessage[]) => {
    // Convert Bindu messages to LangChain format and invoke
    const response = await llm.invoke(
      messages.map((m) => ({ role: m.role, content: m.content }))
    );

    // Return content — Bindu handles the rest
    return typeof response.content === "string"
      ? response.content
      : JSON.stringify(response.content);
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
   └── GrpcAgentClient — makes gRPC call to TypeScript process
6. TypeScript SDK receives HandleMessages on :50052
7. SDK calls your handler(messages)
8. Your handler calls LangChain ChatOpenAI.invoke()
9. LangChain calls OpenAI GPT-4o API
10. Response flows back: LangChain → handler → gRPC → Worker → A2A → Client
```

## Project Structure

```
typescript-langchain-agent/
  index.ts                    # Agent code — LangChain.js + bindufy()
  package.json                # Dependencies (@bindu/sdk, @langchain/openai)
  tsconfig.json               # TypeScript configuration
  .env.example                # Environment variable template
  .env                        # Your actual keys (git-ignored)
  README.md                   # This file
  skills/
    research/
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
pip install bindu
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

## Stop the Agent

Press `Ctrl+C` in the terminal. This kills both the TypeScript process and the Python core.

## Next Steps

- Try the [TypeScript OpenAI Agent](../typescript-openai-agent/) for a direct OpenAI SDK example
- Read the [gRPC Documentation](../../docs/GRPC_LANGUAGE_AGNOSTIC.md) for architecture details
- Check the [SDK README](../../sdks/typescript/README.md) for full API reference
- Build your own agent: copy this folder, change the handler, run `bindufy()`
