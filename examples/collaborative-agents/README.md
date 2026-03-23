# Bindu Collaborative Agents

A working multi-agent system demonstrating the **Internet of Agents** using the Bindu framework.

Three specialized agents collaborate to answer questions — each with its own DID identity,
communicating over the A2A protocol.

---

## System Architecture

```
User Query
    ↓
Coordinator Agent (port 3775)
    ↓               ↓
Memory Agent    Research Agent
(port 3774)     (port 3773)
    ↓               ↓
Semantic        DuckDuckGo
Retrieval       Web Search
```

**Flow:**
1. User sends query to Coordinator
2. Coordinator checks Memory Agent (semantic similarity search)
3. If found in memory → return instantly
4. If not found → Research Agent searches the web
5. Answer stored in Memory Agent for future queries
6. Response returned to user

---

## Agents

### Research Agent (port 3773)
Searches the web using DuckDuckGo and answers questions using an LLM via OpenRouter.
Specialized in the Bindu AI framework and Internet of Agents concepts.

### Memory Agent (port 3774)
Stores and retrieves knowledge using vector embeddings and cosine similarity.
Uses `text-embedding-3-small` via OpenRouter. Threshold of 0.75 similarity
ensures only relevant memories are returned.

Commands:
- `store:<text>` — stores text in semantic memory
- `retrieve:<query>` — retrieves most similar memory

### Coordinator Agent (port 3775)
Orchestrates the other two agents. Checks memory first, falls back to research,
stores new knowledge automatically. Each call uses the A2A `message/send` protocol.

---

## Prerequisites

- Python 3.12+
- OpenRouter API key (free tier works): https://openrouter.ai

---

## Installation

```bash
git clone https://github.com/Subhajitdas99/bindu-collaborative-agents.git
cd bindu-collaborative-agents
pip install -r requirements.txt
```

Set your API key:

```bash
# Linux/macOS
export OPENROUTER_API_KEY="your-api-key"

# Windows PowerShell
$env:OPENROUTER_API_KEY="your-api-key"
```

Or create a `.env` file:

```
OPENROUTER_API_KEY=your-api-key
BINDU_AUTHOR=your.email@example.com
```

---

## Running

Open **3 separate terminals** and run one agent in each:

**Terminal 1 — Research Agent**
```bash
python research_agent.py
```

**Terminal 2 — Memory Agent**
```bash
python memory_agent.py
```

**Terminal 3 — Coordinator Agent**
```bash
python coordinator_agent.py
```

---

## Testing

Send a query to the coordinator (Terminal 4):

**Linux/macOS:**
```bash
curl -X POST http://localhost:3775/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What is Bindu?"}],
        "kind": "message",
        "messageId": "11111111-1111-1111-1111-111111111111",
        "contextId": "11111111-1111-1111-1111-111111111112",
        "taskId": "11111111-1111-1111-1111-111111111113"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "11111111-1111-1111-1111-111111111114"
  }'
```

**Windows PowerShell:**
```powershell
Invoke-WebRequest -Uri "http://localhost:3775/" `
  -Method POST `
  -ContentType "application/json" `
  -UseBasicParsing `
  -Body '{"jsonrpc":"2.0","method":"message/send","params":{"message":{"role":"user","parts":[{"kind":"text","text":"What is Bindu?"}],"kind":"message","messageId":"11111111-1111-1111-1111-111111111111","contextId":"11111111-1111-1111-1111-111111111112","taskId":"11111111-1111-1111-1111-111111111113"},"configuration":{"acceptedOutputModes":["application/json"]}},"id":"11111111-1111-1111-1111-111111111114"}' | Select-Object -ExpandProperty Content
```

Wait 15-20 seconds (research takes time), then poll for the result:

**Linux/macOS:**
```bash
curl -X POST http://localhost:3775/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {"taskId": "11111111-1111-1111-1111-111111111113"},
    "id": "11111111-1111-1111-1111-111111111115"
  }'
```

**Windows PowerShell:**
```powershell
Invoke-WebRequest -Uri "http://localhost:3775/" `
  -Method POST `
  -ContentType "application/json" `
  -UseBasicParsing `
  -Body '{"jsonrpc":"2.0","method":"tasks/get","params":{"taskId":"11111111-1111-1111-1111-111111111113"},"id":"11111111-1111-1111-1111-111111111115"}' | Select-Object -ExpandProperty Content
```

---

## Expected Output

First query (cache miss — researches the web):
```json
{
  "result": {
    "status": {"state": "completed"},
    "artifacts": [{
      "parts": [{
        "kind": "text",
        "text": "The Bindu AI Framework is designed to facilitate the creation of
                 intelligent and interoperable AI agents..."
      }]
    }]
  }
}
```

Second identical query (cache hit — served from memory instantly):
```json
{
  "result": {
    "artifacts": [{
      "parts": [{"kind": "text", "text": "(From Memory) The Bindu AI Framework..."}]
    }]
  }
}
```

---

## What This Demonstrates

- **Agent-to-Agent (A2A) communication** over HTTP using the Bindu protocol
- **DID identity** — each agent gets a unique Decentralized Identifier
- **Semantic memory** — knowledge retrieved by meaning, not keyword matching
- **Coordinator pattern** — orchestration without tight coupling
- **Internet of Agents** — agents discovering and calling each other

---

## Project Structure

```
collaborative-agents/
├── coordinator_agent.py     — orchestrates research + memory agents
├── research_agent.py        — web search via DuckDuckGo
├── memory_agent.py          — semantic memory store/retrieve
├── requirements.txt
├── .env                     — API keys (not committed)
├── .gitignore
└── utils/
    └── semantic_memory.py   — embeddings + cosine similarity
```

---

## Technologies

- [Bindu](https://github.com/getbindu/bindu) — Internet of Agents framework
- [Agno](https://github.com/agno-agi/agno) — agent framework
- [OpenRouter](https://openrouter.ai) — LLM + embeddings API
- [DuckDuckGo](https://pypi.org/project/duckduckgo-search/) — web search
- NumPy — cosine similarity computation

---

## Author

**Subhajit Das**
Final Year B.Tech AI/ML Student
Interested in Multi-Agent Systems, AI Infrastructure, and Autonomous Agents.

GitHub: [@Subhajitdas99](https://github.com/Subhajitdas99)