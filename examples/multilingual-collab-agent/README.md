# Multilingual Collaborative Agent

An identity-aware AI agent built on the [Bindu framework](https://github.com/getbindu/bindu) that detects the user's language and responds naturally in English, Hindi (हिन्दी), or Bengali (বাংলা).

Demonstrates how a single Bindu agent can serve users across language barriers using DID identity, Mem0 persistent memory, and structured skills.

---

## Features

- **Automatic language detection** — detects EN / HI / BN and responds in the same language
- **DID identity** — each agent instance gets a unique Bindu Decentralized Identifier
- **Persistent memory** — remembers context across sessions using Mem0
- **Web research** — searches the web via DuckDuckGo in any supported language
- **3 skills** — research, translate, collaborate

---

## Architecture

```
User Message (any language)
        ↓
Bindu Server (port 3773)
        ↓
Multilingual Agent Handler
        ↓
Language Detection → EN / HI / BN
        ↓
    ┌───┴──────────────┐
    │                  │
DuckDuckGo         Mem0 Memory
(web search)    (persistent context)
    │                  │
    └───┬──────────────┘
        ↓
Response in detected language
```

---

## Skills

| Skill | Description |
|-------|-------------|
| `research` | Web search via DuckDuckGo — answers factual queries in EN/HI/BN |
| `translate` | Translates text between English, Hindi, and Bengali |
| `collaborate` | Drafts messages, emails, and documents in any supported language |

---

## Prerequisites

- Python 3.12+
- [OpenRouter API key](https://openrouter.ai) (free tier works)
- [Mem0 API key](https://app.mem0.ai/dashboard/api-keys) (free tier available)

---

## Setup

```bash
# Clone Bindu and navigate to this example
git clone https://github.com/getbindu/bindu.git
cd bindu/examples/multilingual-collab-agent

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API keys
```

`.env` file:
```
OPENROUTER_API_KEY=your_openrouter_key
MEM0_API_KEY=your_mem0_key
MODEL_NAME=openai/gpt-4o-mini
```

---

## Run

```bash
python main.py
```

Agent starts at `http://localhost:3773`

Agent card: `http://localhost:3773/.well-known/agent.json`

---

## Test

**English query:**

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What is the Bindu framework?"}],
        "kind": "message",
        "messageId": "00000000-0000-0000-0000-000000000001",
        "contextId": "00000000-0000-0000-0000-000000000002",
        "taskId": "00000000-0000-0000-0000-000000000003"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "00000000-0000-0000-0000-000000000004"
  }'
```

**Hindi query:**

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "बिंदू फ्रेमवर्क क्या है?"}],
        "kind": "message",
        "messageId": "00000000-0000-0000-0000-000000000011",
        "contextId": "00000000-0000-0000-0000-000000000012",
        "taskId": "00000000-0000-0000-0000-000000000013"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "00000000-0000-0000-0000-000000000014"
  }'
```

**Bengali query:**

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "বিন্দু ফ্রেমওয়ার্ক কী?"}],
        "kind": "message",
        "messageId": "00000000-0000-0000-0000-000000000021",
        "contextId": "00000000-0000-0000-0000-000000000022",
        "taskId": "00000000-0000-0000-0000-000000000023"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "00000000-0000-0000-0000-000000000024"
  }'
```

**Windows PowerShell:**

```powershell
Invoke-WebRequest -Uri "http://localhost:3773/" `
  -Method POST -ContentType "application/json" -UseBasicParsing `
  -Body '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"बिंदू फ्रेमवर्क क्या है?"}],"kind":"message","messageId":"11111111-1111-1111-1111-111111111111","contextId":"11111111-1111-1111-1111-111111111112","taskId":"11111111-1111-1111-1111-111111111113"},"configuration":{"acceptedOutputModes":["application/json"]}},"id":"11111111-1111-1111-1111-111111111114"}' | Select-Object -ExpandProperty Content
```

Then poll for the result:

```powershell
Start-Sleep -Seconds 15
Invoke-WebRequest -Uri "http://localhost:3773/" `
  -Method POST -ContentType "application/json" -UseBasicParsing `
  -Body '{"jsonrpc":"2.0","method":"tasks/get","params":{"taskId":"11111111-1111-1111-1111-111111111113"},"id":"11111111-1111-1111-1111-111111111115"}' | Select-Object -ExpandProperty Content
```

---

## Expected Behavior

| Input Language | Response Language |
|---------------|-------------------|
| English | English |
| हिन्दी (Hindi) | हिन्दी |
| বাংলা (Bengali) | বাংলা |

The agent detects language automatically — no configuration needed.

---

## What This Demonstrates

- **Framework-agnostic bindufying** — Agno agent wrapped with `bindufy()` in one call
- **DID identity** — agent is discoverable in the Internet of Agents ecosystem
- **Persistent memory** — Mem0 remembers context across conversations
- **Multilingual AI** — single agent serving users in 3 languages
- **Skill-based architecture** — research, translate, collaborate as separate skills

---

## Dependencies

- [Bindu](https://github.com/getbindu/bindu) — Internet of Agents framework
- [Agno](https://github.com/agno-agi/agno) — agent framework
- [OpenRouter](https://openrouter.ai) — LLM API
- [Mem0](https://mem0.ai) — persistent agent memory
- [DuckDuckGo Search](https://pypi.org/project/duckduckgo-search/) — web search

---

## Related Examples

- [`examples/collaborative-agents/`](../collaborative-agents/) — multi-agent A2A communication
- [`examples/beginner/`](../beginner/) — simple single-agent examples
- [`examples/agent_swarm/`](../agent_swarm/) — agent swarm patterns
