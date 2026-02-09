# Bindu Frontend Integration Plan

This document provides a detailed plan for integrating the chat-ui frontend with the Bindu A2A Protocol backend.

---

## 1. Architecture Overview

### Current State: Chat-UI (HuggingFace)

```
┌─────────────────────────────────────────────────────────────┐
│                        Chat-UI                               │
├─────────────────────────────────────────────────────────────┤
│  Frontend (SvelteKit)                                        │
│  ├── src/routes/conversation/[id]/+server.ts (POST handler) │
│  ├── src/lib/components/chat/ (UI components)               │
│  └── src/lib/stores/ (Svelte reactive state)                │
├─────────────────────────────────────────────────────────────┤
│  Backend Integration Layer                                   │
│  ├── src/lib/server/endpoints/openai/ (OpenAI adapter)      │
│  ├── src/lib/server/textGeneration/ (streaming pipeline)    │
│  ├── src/lib/server/models.ts (model discovery)             │
│  └── src/lib/server/database.ts (MongoDB persistence)       │
├─────────────────────────────────────────────────────────────┤
│                    OpenAI Protocol                           │
│  GET  /models → list available models                        │
│  POST /chat/completions → send messages, get streaming response
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │   OpenAI-Compatible Backend   │
              │   (HF Router, Ollama, etc.)   │
              └───────────────────────────────┘
```

### Target State: Chat-UI + Bindu

```
┌─────────────────────────────────────────────────────────────┐
│                        Chat-UI                               │
├─────────────────────────────────────────────────────────────┤
│  Frontend (SvelteKit) - NO CHANGES NEEDED                   │
│  ├── src/routes/conversation/[id]/+server.ts                │
│  ├── src/lib/components/chat/                               │
│  └── src/lib/stores/                                        │
├─────────────────────────────────────────────────────────────┤
│  Backend Integration Layer                                   │
│  ├── src/lib/server/endpoints/openai/ (keep for other LLMs)│
│  ├── src/lib/server/endpoints/bindu/ ← NEW ADAPTER          │
│  ├── src/lib/server/textGeneration/                         │
│  ├── src/lib/server/models.ts ← MODIFY for agent discovery  │
│  └── src/lib/server/database.ts                             │
├─────────────────────────────────────────────────────────────┤
│              Bindu Endpoint Adapter (NEW)                    │
│  Translates: OpenAI Protocol ←→ A2A JSON-RPC Protocol       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      Bindu Backend            │
              │   (A2A Protocol / JSON-RPC)   │
              │   POST / → message/send       │
              │   GET /.well-known/agent.json │
              └───────────────────────────────┘
```

---

## 2. Protocol Translation Reference

### 2.1 Model/Agent Discovery

| Chat-UI (OpenAI) | Bindu (A2A) |
|------------------|-------------|
| `GET /models` | `GET /.well-known/agent.json` |

**OpenAI Response:**
```json
{
  "data": [
    {"id": "gpt-4", "description": "..."}
  ]
}
```

**Bindu Response (Agent Card):**
```json
{
  "name": "First Agent",
  "description": "A helpful AI agent",
  "version": "1.0.0",
  "did": "did:bindu:...",
  "capabilities": {
    "streaming": true,
    "taskManagement": true
  },
  "skills": [
    {"id": "question-answering-v1", "name": "Question Answering"}
  ],
  "endpoints": {
    "jsonrpc": "http://localhost:3773/"
  }
}
```

**Translation Logic:**
```typescript
// In models.ts - agentCardToModel()
const agentCard = await fetch(`${BINDU_BASE_URL}/.well-known/agent.json`).then(r => r.json());
return {
  id: agentCard.did || agentCard.name,
  name: agentCard.name,
  displayName: agentCard.name,
  description: agentCard.description,
  endpoints: [{ type: "bindu", baseURL: agentCard.endpoints.jsonrpc }],
  supportsTools: agentCard.capabilities?.taskManagement ?? false,
  multimodal: false, // extend later if Bindu supports images
};
```

---

### 2.2 Message Sending

| Chat-UI (OpenAI) | Bindu (A2A) |
|------------------|-------------|
| `POST /chat/completions` | `POST /` with `method: "message/send"` |

**OpenAI Request:**
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are helpful"},
    {"role": "user", "content": "Hello"}
  ],
  "stream": true
}
```

**Bindu JSON-RPC Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"kind": "text", "text": "Hello"}],
      "kind": "message",
      "messageId": "uuid-1",
      "contextId": "conv-id",
      "taskId": "uuid-2"
    },
    "configuration": {
      "acceptedOutputModes": ["application/json"]
    }
  },
  "id": "request-uuid"
}
```

**Translation Logic (pseudocode):**
```typescript
// Convert chat-ui messages to Bindu format
function chatUIToBindu(messages: Message[], convId: string): BinduRequest {
  const lastUserMessage = messages.filter(m => m.from === "user").pop();

  return {
    jsonrpc: "2.0",
    method: "message/send",
    params: {
      message: {
        role: "user",
        parts: [{ kind: "text", text: lastUserMessage.content }],
        kind: "message",
        messageId: crypto.randomUUID(),
        contextId: convId,  // Map to conversation._id
        taskId: crypto.randomUUID(),
      },
      configuration: {
        acceptedOutputModes: ["application/json"]
      }
    },
    id: crypto.randomUUID()
  };
}
```

---

### 2.3 Response Handling

**Bindu JSON-RPC Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "task": {
      "taskId": "uuid",
      "contextId": "conv-id",
      "status": {"state": "completed", "timestamp": "..."},
      "artifacts": [
        {"kind": "text", "text": "Hello! How can I help you?"}
      ]
    }
  },
  "id": "request-uuid"
}
```

**Translation to Chat-UI TextGenerationStream:**
```typescript
async function* binduToTextGenerationStream(
  response: BinduResponse
): AsyncGenerator<TextGenerationStreamOutput> {
  const task = response.result.task;

  for (const artifact of task.artifacts) {
    if (artifact.kind === "text") {
      // Emit the text as a single token (or chunk it)
      yield {
        token: { text: artifact.text, special: false },
        generated_text: artifact.text,
      };
    }
  }
}
```

---

### 2.4 Streaming Support

If Bindu supports streaming via `message/stream`:

```typescript
// For streaming responses
async function* binduStreamToTextGeneration(
  eventSource: EventSource
): AsyncGenerator<TextGenerationStreamOutput> {
  for await (const event of eventSource) {
    const data = JSON.parse(event.data);
    if (data.result?.task?.status?.state === "working") {
      // Partial result
      yield {
        token: { text: data.result.task.artifacts?.[0]?.text || "", special: false },
      };
    } else if (data.result?.task?.status?.state === "completed") {
      // Final result
      yield {
        token: { text: "", special: true },
        generated_text: data.result.task.artifacts?.[0]?.text || "",
      };
    }
  }
}
```

---

## 3. Files to Create/Modify

### 3.1 NEW FILES

| File | Purpose |
|------|---------|
| `src/lib/server/endpoints/bindu/endpointBindu.ts` | Main Bindu endpoint adapter |
| `src/lib/server/endpoints/bindu/binduToTextGenerationStream.ts` | Response stream converter |
| `src/lib/server/endpoints/bindu/types.ts` | Bindu-specific TypeScript types |

### 3.2 FILES TO MODIFY

| File | Changes |
|------|---------|
| `src/lib/server/endpoints/endpoints.ts` | Register `bindu` endpoint type |
| `src/lib/server/models.ts` | Add Bindu agent discovery logic |
| `.env` | Add `BINDU_BASE_URL`, `BINDU_API_KEY` variables |

---

## 4. Implementation Steps

### Phase 1: Core Bindu Endpoint (Day 1-2)

1. **Create `src/lib/server/endpoints/bindu/types.ts`**
   - Define TypeScript interfaces for A2A protocol
   - `BinduMessage`, `BinduTask`, `BinduArtifact`, `AgentCard`

2. **Create `src/lib/server/endpoints/bindu/endpointBindu.ts`**
   - Implement `endpointBindu()` function matching `Endpoint` signature
   - Handle message translation (chat-ui → Bindu)
   - Make JSON-RPC call to Bindu backend
   - Return async generator for response

3. **Create `src/lib/server/endpoints/bindu/binduToTextGenerationStream.ts`**
   - Convert Bindu task response to `TextGenerationStreamOutput`
   - Handle both sync and streaming responses

4. **Update `src/lib/server/endpoints/endpoints.ts`**
   ```typescript
   import { endpointBindu, endpointBinduParametersSchema } from "./bindu/endpointBindu";

   export const endpoints = {
     openai: endpointOai,
     bindu: endpointBindu,  // Add this
   };

   export const endpointSchema = z.discriminatedUnion("type", [
     endpointOAIParametersSchema,
     endpointBinduParametersSchema,  // Add this
   ]);
   ```

### Phase 2: Agent Discovery (Day 2-3)

5. **Update `src/lib/server/models.ts`**
   - Add `fetchBinduAgents()` function
   - Fetch from `/.well-known/agent.json`
   - Convert agent card to `ModelConfig`
   - Merge with OpenAI models if both configured

6. **Update `.env`**
   ```env
   # Bindu Agent Configuration
   BINDU_BASE_URL=http://localhost:3773
   BINDU_API_KEY=  # Optional, for Bearer auth
   BINDU_AGENT_NAME=Bindu Agent  # Display name override
   ```

### Phase 3: Context Management (Day 3-4)

7. **Map conversation IDs**
   - Use MongoDB `conversation._id` as Bindu `contextId`
   - Store `taskId` in message metadata for task tracking

8. **Implement task status checking**
   - Optional: poll `tasks/get` for long-running tasks
   - Update message with task state

### Phase 4: Testing & Polish (Day 4-5)

9. **Test scenarios**
   - Single message send/receive
   - Multi-turn conversation
   - Error handling
   - Task cancellation

10. **UI enhancements (optional)**
    - Show agent skills in UI
    - Display task status indicators
    - Add Bindu-specific settings

---

## 5. Environment Variables

Add these to `.env`:

```env
### Bindu Agent Configuration ###
# Base URL of the Bindu agent server
BINDU_BASE_URL=http://localhost:3773

# API key for authenticated requests (optional)
BINDU_API_KEY=

# Override display name for the agent in the model list
BINDU_AGENT_NAME=

# Set to "true" to use Bindu as the default/only model
BINDU_ONLY_MODE=false

# Timeout for Bindu requests in milliseconds
BINDU_TIMEOUT_MS=30000
```

---

## 6. Key Code Snippets

### 6.1 Bindu Endpoint Schema

```typescript
// src/lib/server/endpoints/bindu/endpointBindu.ts
import { z } from "zod";
import type { Endpoint } from "../endpoints";
import { binduToTextGenerationStream } from "./binduToTextGenerationStream";

export const endpointBinduParametersSchema = z.object({
  type: z.literal("bindu"),
  baseURL: z.string().url(),
  apiKey: z.string().optional(),
  model: z.any(),
});

export async function endpointBindu(
  input: z.input<typeof endpointBinduParametersSchema>
): Promise<Endpoint> {
  const { baseURL, apiKey, model } = endpointBinduParametersSchema.parse(input);

  return async ({ messages, conversationId, abortSignal }) => {
    const lastUserMessage = messages.filter(m => m.from === "user").pop();
    if (!lastUserMessage) throw new Error("No user message found");

    const binduRequest = {
      jsonrpc: "2.0",
      method: "message/send",
      params: {
        message: {
          role: "user",
          parts: [{ kind: "text", text: lastUserMessage.content }],
          kind: "message",
          messageId: crypto.randomUUID(),
          contextId: conversationId?.toString() || crypto.randomUUID(),
          taskId: crypto.randomUUID(),
        },
        configuration: {
          acceptedOutputModes: ["application/json"],
        },
      },
      id: crypto.randomUUID(),
    };

    const response = await fetch(baseURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      body: JSON.stringify(binduRequest),
      signal: abortSignal,
    });

    if (!response.ok) {
      throw new Error(`Bindu request failed: ${response.status}`);
    }

    const binduResponse = await response.json();
    return binduToTextGenerationStream(binduResponse);
  };
}
```

### 6.2 Stream Converter

```typescript
// src/lib/server/endpoints/bindu/binduToTextGenerationStream.ts
import type { TextGenerationStreamOutput } from "@huggingface/inference";

interface BinduResponse {
  jsonrpc: "2.0";
  result?: {
    task: {
      taskId: string;
      status: { state: string };
      artifacts?: Array<{ kind: string; text?: string }>;
    };
  };
  error?: { code: number; message: string };
}

export async function* binduToTextGenerationStream(
  response: BinduResponse
): AsyncGenerator<TextGenerationStreamOutput, void, void> {
  if (response.error) {
    throw new Error(`Bindu error ${response.error.code}: ${response.error.message}`);
  }

  const task = response.result?.task;
  if (!task) {
    throw new Error("No task in Bindu response");
  }

  const textArtifact = task.artifacts?.find(a => a.kind === "text");
  const text = textArtifact?.text || "";

  // Emit as final answer
  yield {
    token: { text, special: false, id: 0 },
    generated_text: text,
    details: null,
  };
}
```

---

## 7. Testing Checklist

- [ ] Agent discovery: fetch and display agent from `/.well-known/agent.json`
- [ ] Simple message: send "Hello" and receive response
- [ ] Multi-turn: context is preserved across messages
- [ ] Error handling: graceful failure on network/auth errors
- [ ] Abort: user can cancel in-progress generation
- [ ] Task status: handle pending/working/completed states
- [ ] Mixed mode: Bindu + OpenAI models work together (if enabled)

---

## 8. Future Enhancements

1. **Streaming support** - Implement `message/stream` for real-time responses
2. **File handling** - Support `kind: "file"` artifacts
3. **Skills UI** - Show available agent skills in the interface
4. **Payment integration** - x402 payment flow for paid agents
5. **DID resolution** - Display agent DID and verification
6. **Task history** - Show task states and allow retry/cancel

---

## 9. Quick Start

```bash
# Navigate to frontend
cd /Users/raahuldutta/Documents/GetBindu/Bindu/frontend

# Install dependencies
npm install

# Configure environment
cp .env .env.local
# Edit .env.local and set BINDU_BASE_URL

# Start development server
npm run dev
```

---

*Generated: 2026-02-07*
*Source: HuggingFace chat-ui + Bindu A2A Protocol analysis*
