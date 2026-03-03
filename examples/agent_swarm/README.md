# 🌻 Bindu NightSky Swarm

**A production-grade multi-agent system combining agno orchestration with LangGraph pipelines — deployed on Bindu's identity, communication & payments layer for AI agents.**

---

## 🌍 Why This Exists

Most AI systems are a single LLM call with a long prompt. That approach:

- Scales poorly
- Is brittle under failure
- Cannot self-correct
- Cannot coordinate complex workflows

**Future AI systems will be societies of specialized agents.**

This project proves that vision in running code — agents that plan, research, search the web, analyze, critique, reflect, and publish — autonomously, on a Redis-backed distributed scheduler.

---

## 🏗️ Architecture

The NightSky Swarm has two layers that run in sequence:

### Layer 1 — agno Orchestrator (Planning + Research + Critique)

| Agent | Framework | Role |
|-------|-----------|------|
| **Planner** | agno + Gemini | Decomposes user query into structured steps |
| **Researcher** | agno + Gemini | Deep factual research on the topic |
| **Summarizer** | agno + Gemini | Condenses research into clear explanation |
| **Critic** | agno + Gemini | Reviews, challenges, and refines output |
| **Reflection** | agno + Gemini | Evaluates quality, triggers retry if needed |

### Layer 2 — LangGraph Pipeline (Scout → Analyst → Publisher)

| Agent | Framework | Role |
|-------|-----------|------|
| **Scout** | LangGraph ReAct + DuckDuckGo | Live web research using ReAct reasoning loop |
| **Analyst** | LangGraph LCEL chain | Extracts claims, scores confidence, returns structured JSON |
| **Publisher** | LangGraph output chain | Formats clean markdown report, saves to file |

### Execution Flow

```
User Query (via A2A protocol)
    ↓
┌─────────────────────────────────────────────┐
│           agno Orchestrator Layer            │
│  Planner → Researcher → Summarizer →        │
│  Critic → Reflection Agent                  │
│  Quality: GOOD? ✅ → continue               │
│  Quality: LOW?  🔄 → retry (max 2x)         │
└─────────────────────────────────────────────┘
    ↓  (on GOOD quality)
┌─────────────────────────────────────────────┐
│          LangGraph Pipeline Layer            │
│  Scout (ReAct web search)                   │
│      ↓                                      │
│  Analyst (claim extraction + confidence)    │
│      ↓                                      │
│  Publisher (markdown report + file save)    │
└─────────────────────────────────────────────┘
    ↓
Final markdown report saved to reports/
```

---

## 🔧 Infrastructure

### Redis Scheduler (Production-Grade)
- Tasks survive restarts — persistent Redis queue
- Exponential backoff on Redis errors (2s → 4s → 8s → 30s max)
- `redis.RedisError` treated as retryable — 3 attempts with exponential wait
- W3C `traceparent` propagation — distributed traces connected end-to-end

### Bindu Integration
- Every agent gets a **unique DID** — identity-first design
- A2A protocol endpoints — agents communicate via standard HTTP
- OpenTelemetry spans — full observability from task submission to completion
- Redis scheduler wired via config — no code changes needed to switch backends

---

## 📁 Project Structure

```
examples/agent_swarm/
├── bindu_super_agent.py     # Entry point — deploys full swarm on Bindu
├── orchestrator.py          # agno pipeline coordinator
│
├── planner_agent.py         # agno: task decomposition
├── researcher_agent.py      # agno: deep research
├── summarizer_agent.py      # agno: condensation
├── critic_agent.py          # agno: review & refinement
├── reflection_agent.py      # agno: self-evaluation
│
├── scout_agent.py           # LangGraph ReAct: live web search
├── analyst_agent.py         # LangGraph LCEL: structured analysis
├── publisher_agent.py       # LangGraph: markdown report generation
│
└── reports/                 # Auto-generated research reports (timestamped)
```

---

## 🚀 How To Run

### 1. Setup

```bash
git clone https://github.com/getbindu/bindu.git
cd bindu
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e .
pip install langchain langgraph langchain-community langchain-google-genai
```

### 2. Start Redis

```bash
# macOS
brew install redis && redis-server

# Windows (WSL or Docker)
docker run -p 6379:6379 redis
```

### 3. Configure environment

Create `examples/agent_swarm/.env`:

```bash
GOOGLE_API_KEY=your_gemini_key
REDIS_URL=redis://localhost:6379

# Optional — autonomous scheduled research
SWARM_AUTONOMOUS_MODE=true
SWARM_RESEARCH_TOPIC=latest developments in AI agents and multi-agent systems
SWARM_RESEARCH_INTERVAL_HOURS=6
```

### 4. Run the swarm

```bash
python -m examples.agent_swarm.bindu_super_agent
```

### 5. Send a query

```bash
curl -X POST http://localhost:3780 \
  -H "Content-Type: application/json" \
  -d '{"message": {"role": "user", "parts": [{"type": "text", "text": "What is agentic AI?"}]}}'
```

Or open the interactive UI:
```
http://localhost:3780/docs
```

---

## 🔬 What Makes This Different

### Two frameworks, one pipeline
agno handles planning and orchestration. LangGraph handles live web research and structured analysis. Each does what it's best at.

### Self-correcting intelligence
The Reflection Agent evaluates output quality after every cycle. If quality is low, the entire pipeline retries with a refined query — up to 2 times automatically.

### Production-ready infrastructure
- Redis scheduler with exponential backoff — survives Redis restarts
- W3C distributed tracing — full observability across agent boundaries
- Graceful fallbacks at every stage — one agent failing doesn't crash the pipeline

### Reports on disk
Every successful research cycle produces a timestamped markdown report in `reports/` — a permanent artifact of what the swarm discovered.

---

## 📊 Protocol Endpoints

When running, the swarm exposes:

| Endpoint | Description |
|----------|-------------|
| `POST /` | Send task (A2A protocol) |
| `GET /.well-known/agent.json` | Agent discovery |
| `GET /agent/info` | Agent metadata |
| `POST /did/resolve` | DID resolution |
| `GET /docs` | Interactive UI |

---

## 🔮 Roadmap

- [ ] Scout, Analyst, Publisher as independent Bindu microservices (separate ports)
- [ ] A2A inter-agent communication between all three layers
- [ ] Trust & reputation scoring between agents
- [ ] Payment layer — paid research tasks via Bindu X402
- [ ] Cross-agent memory with persistent vector store

---

## 🌻 The Bigger Picture

Bindu is building identity, communication, and payments for AI agents.

This swarm demonstrates all three layers working together in production:

- **Identity** — every agent has a DID, every task is traceable
- **Communication** — A2A protocol, W3C traces, structured JSON between agents
- **Infrastructure** — Redis scheduler, exponential backoff, graceful failure handling

> Intelligence emerges from collaboration — not model size.
