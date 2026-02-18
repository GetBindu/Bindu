# 🤝 Collab Pipeline — Multi-Agent A2A Communication

A complete example demonstrating **two Bindu agents collaborating via the A2A protocol**. This is the first example in the repo showing inter-agent HTTP communication — the core value proposition of Bindu.

## Architecture

```
┌──────────────┐    A2A JSON-RPC     ┌──────────────────┐    A2A JSON-RPC     ┌──────────────────┐
│              │   message/send      │                  │   message/send      │                  │
│ Orchestrator ├────────────────────►│ Summarizer Agent ├────────────────────►│ Translator Agent │
│   (client)   │◄────────────────────┤   (port 3773)    │◄────────────────────┤   (port 3774)    │
│              │    tasks/get        │                  │    tasks/get        │                  │
└──────────────┘                     └──────────────────┘                     └──────────────────┘

Pipeline: User Text → Summary (English) → Translation (Spanish)
```

## How It Works

1. **Summarizer Agent** (`port 3773`) — Accepts text, returns concise bullet-point summary
2. **Translator Agent** (`port 3774`) — Accepts text, returns Spanish translation
3. **Orchestrator** — A2A client that chains both agents:
   - Sends text to Summarizer via `message/send`
   - Polls via `tasks/get` until task completes
   - Extracts summary from task artifacts
   - Sends summary to Translator via `message/send`
   - Polls and extracts final translation

## Quick Start

### Prerequisites

- Python 3.12+
- [UV package manager](https://github.com/astral-sh/uv)
- Bindu installed (`uv add bindu`)
- An `OPENROUTER_API_KEY` (free at [openrouter.ai](https://openrouter.ai))

### Setup

```bash
# From the repo root
cd examples/collab_pipeline

# Copy and configure environment variables
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### Run

Open **three terminals** from the repo root:

```bash
# Terminal 1: Start the Summarizer Agent
python examples/collab_pipeline/summarizer_agent.py

# Terminal 2: Start the Translator Agent
python examples/collab_pipeline/translator_agent.py

# Terminal 3: Run the Orchestrator
python examples/collab_pipeline/collab_orchestrator.py
```

### Expected Output

```
======================================================================
🚀 Bindu Collab Pipeline — Summarize → Translate
======================================================================

📄 Original Text (142 words):
--------------------------------------------------
Artificial intelligence (AI) has rapidly evolved...

======================================================================
📝 Stage 1: Sending to Summarizer Agent (port 3773)
======================================================================
  📨 Task submitted: abc-123 (state=submitted)
  ⏳ Polling... state=working
  ⏳ Polling... state=completed

✅ Summary received:
--------------------------------------------------
• AI has evolved from academic pursuit to industry-transforming force
• Healthcare, finance, and NLP are key application areas
• Ethical concerns include job displacement and algorithmic bias
...

======================================================================
🌍 Stage 2: Sending to Translator Agent (port 3774)
======================================================================
  📨 Task submitted: def-456 (state=submitted)
  ⏳ Polling... state=completed

✅ Translation received:
--------------------------------------------------
• La IA ha evolucionado de búsqueda académica a fuerza transformadora...

======================================================================
🎉 Pipeline Complete!
======================================================================
```

## Custom Input

Pass your own text as a command-line argument:

```bash
python examples/collab_pipeline/collab_orchestrator.py "Your text here..."
```

## Key Concepts Demonstrated

| Concept | Where |
|---------|-------|
| `bindufy()` agent creation | `summarizer_agent.py`, `translator_agent.py` |
| A2A `message/send` JSON-RPC | `collab_orchestrator.py` |
| A2A `tasks/get` polling | `collab_orchestrator.py` |
| Task artifact extraction | `collab_orchestrator.py` |
| Zero-config (memory storage) | Both agent configs |
| Multi-port agent deployment | Ports 3773 and 3774 |

## Files

| File | Description |
|------|-------------|
| `summarizer_agent.py` | Agent 1 — text summarization service |
| `translator_agent.py` | Agent 2 — text translation service |
| `collab_orchestrator.py` | A2A client connecting both agents |
| `.env.example` | Environment variable template |
