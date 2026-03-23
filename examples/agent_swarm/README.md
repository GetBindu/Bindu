**Welcome to the Internet of Agents. 🌐🤖🌻**

# 🌻 Bindu Agent Swarm

**Building a Living Society of AI Agents**

A production-grade multi-agent system built on top of **Bindu — the identity, communication & payments layer for AI agents.**

This project demonstrates how to design, orchestrate, and deploy a **collaborative society of autonomous AI agents** that can **plan, research, summarize, critique, reflect, and self-improve** — using a protocol-first, composable architecture with **OpenRouter's `openai/gpt-oss-120b` model**.

---

# 🌍 Why Agent Swarms?

Modern AI systems rely on **single LLM calls** with increasingly long prompts.

This approach:

* Scales poorly
* Is brittle
* Lacks self-correction
* Cannot coordinate complex workflows

**Future AI systems will be societies of agents.**

Each agent:

* Has an identity
* Communicates via protocols
* Collaborates with peers
* Negotiates tasks
* Reflects on performance
* Improves collectively

Bindu provides the infrastructure layer for this world.

This project **proves that vision in running code.**

---

# 🧠 Core Idea

Instead of building one massive agent, we build **multiple specialized agents**, each responsible for a distinct cognitive role.

Complex intelligence **emerges from collaboration**, not from a single model.

---

# 🏗️ System Architecture

This swarm consists of **five autonomous agents + one orchestrator**, all powered by **OpenRouter's `openai/gpt-oss-120b` model**:

| Component            | Role                                            |
| -------------------- | ----------------------------------------------- |
| **Planner Agent**    | Breaks a user query into structured tasks       |
| **Research Agent**   | Performs deep factual research                  |
| **Summarizer Agent** | Condenses research into clear explanations      |
| **Critic Agent**     | Reviews, challenges, and refines outputs        |
| **Reflection Agent** | Evaluates quality and triggers self-improvement |
| **Orchestrator**     | Coordinates agent execution pipeline            |

---

# 🔁 Execution Flow

```text
User Query
    ↓
Planner → Task Decomposition
    ↓
Researcher → Information Gathering
    ↓
Summarizer → Condensed Understanding
    ↓
Critic → Quality Review & Refinement
    ↓
Reflection Agent → Self-Evaluation & Feedback
    ↓
Final High-Quality Answer
```

Each stage improves the output — resulting in **self-correcting intelligence**.

---

# � Quick Start

### Prerequisites
- Python 3.12+
- OpenRouter API key
- uv package manager
- Bindu installed in project root

### 1. Set Environment Variables

Create `.env` file in `examples/agent_swarm/`:

```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

```bash
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
```

### 2. Install Dependencies

```bash
# From Bindu root directory
uv sync
```

### 3. Start the Agent Swarm

```bash
# From Bindu root directory
cd examples/agent_swarm
uv run python bindu_super_agent.py
```

The agent swarm will start on `http://localhost:3780`

### 4. Test the Swarm

```bash
curl -X POST http://localhost:3780/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What is quantum computing?"}],
        "kind": "message",
        "messageId": "msg-001",
        "contextId": "ctx-001",
        "taskId": "task-001"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "1"
  }'
```

---

# � Design Philosophy

### 1. Protocol-First Architecture

At scale, agents communicate using **Bindu’s protocol layer**, enabling:

* Identity verification
* Message routing
* Capability negotiation
* Secure execution

> In this example, the orchestrator directly invokes agents locally for simplicity and clarity. This models the execution flow while remaining compatible with future protocol-based inter-agent communication.

---

### 2. Specialization > Monolith

Each agent focuses on a **single cognitive responsibility**, which:

* Improves reasoning quality
* Reduces hallucination
* Enables horizontal scalability
* Allows dynamic agent replacement

---

### 3. Reflection & Self-Improvement

The Reflection Agent evaluates:

* Factual accuracy
* Logical coherence
* Completeness

If quality is low → it **automatically triggers refinement loops**.

---

# 📁 Project Structure

```bash
examples/
└── agent_swarm/
    ├── planner_agent.py        # Task planning & decomposition
    ├── researcher_agent.py     # Deep research agent
    ├── summarizer_agent.py     # Summarization agent
    ├── critic_agent.py         # Review & refinement agent
    ├── reflection_agent.py     # Self-evaluation & improvement agent
    ├── orchestrator.py         # Multi-agent execution pipeline
    ├── bindu_super_agent.py    # Entry point – launches full swarm on Bindu
    ├── skills/
    │   └── agent-swarm-intelligence/
    │       └── skill.yaml     # Bindu skill definition
    ├── .env.example            # Environment variables template
    └── README.md               # This documentation
```

---

# 🛠️ Implementation Overview

## 1️⃣ Agent Construction

Each agent is built using:

```python
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
```

All agents use **OpenRouter's `openai/gpt-oss-120b` model** with temperature settings optimized for their specific roles:

- **Planner**: 0.0 (deterministic JSON output)
- **Researcher**: 0.3 (creative research)
- **Summarizer**: 0.2 (balanced clarity)
- **Critic**: 0.1 (minimal creativity)
- **Reflection**: 0.0 (consistent evaluation)

Each agent follows:

* Clear instructions
* Focused prompts
* Single responsibility principle

---

## 2️⃣ Orchestration Pipeline

The orchestrator defines:

```text
Planner → Researcher → Summarizer → Critic → Reflection → Final Output
```

This pipeline:

* Converts chaos → structure
* Turns vague ideas → production-grade outputs
* Enables automatic self-correction

---

## 3️⃣ Bindu Integration

The swarm is deployed using **Bindu’s agent runtime**, enabling:

* DID-based agent identity
* Protocol-based communication
* Future-ready support for economic agents

---

# 🚀 How To Run

## 1️⃣ Setup Environment

```bash
git clone https://github.com/getbindu/bindu.git
cd bindu
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e .
```

---

## 2️⃣ Configure API Keys

### OpenAI

```bash
# Windows
setx OPENAI_API_KEY "your_openai_key"
setx GOOGLE_API_KEY "your_gemini_key"

# macOS / Linux
export OPENAI_API_KEY="your_openai_key"  # pragma: allowlist secret
export GOOGLE_API_KEY="your_gemini_key"  # pragma: allowlist secret
```

### OpenRouter (Optional)

```bash
# Windows
setx OPENAI_API_BASE "https://openrouter.ai/api/v1"
setx OPENAI_API_KEY "your_openrouter_key"

# macOS / Linux
export OPENAI_API_BASE="https://openrouter.ai/api/v1"
export OPENAI_API_KEY="your_openrouter_key"  # pragma: allowlist secret
```

---

## 3️⃣ Run the Swarm

```bash
python examples/agent_swarm/bindu_super_agent.py
```

---

## 4️⃣ Open Interactive UI

```text
http://localhost:3780/docs
```

Bindu provides a **custom interactive chat UI** instead of traditional FastAPI Swagger docs.

---

# 🧪 Example Query

```
Research about Hyderabad, Telangana
```

The system will:

* Plan
* Research
* Summarize
* Critique
* Reflect
* Improve
* Respond

Producing a **high-quality, self-corrected answer.**

---

# 🌻 How This Demonstrates Bindu’s Vision

Bindu is building:

> Identity + Communication + Payments for AI agents

This project validates:

### ✅ Identity Layer

* Every agent receives a **unique DID**
* Enables trust, authentication, and discovery

### ✅ Communication Layer

* Protocol-based messaging
* Multi-agent coordination

### ✅ Collaboration Layer

* Dynamic role assignment
* Agent-to-agent critique
* Self-improving workflows

### 🚀 Future Payment Layer (Ready)

* Architecture supports:

  * Paid agent services
  * Usage billing
  * Execution monetization

---

# 🔮 Roadmap Extensions

* Multi-agent negotiation protocols
* Trust & reputation scoring
* Economic agent marketplaces
* Distributed agent swarms
* Cross-agent memory systems

---

# 🧬 Philosophy

Most AI platforms build:

> Bigger models.

Bindu builds:

> Better systems.

This project proves:

> **Intelligence emerges from collaboration — not model size.**

---

# ⭐ Why This Example Exists

To help developers:

* Understand protocol-first agent design
* Learn how to build real agent societies
* Build production-grade agent workflows
* Ship real multi-agent systems

---

# 🌍 The Bigger Picture

This swarm is **not a demo**.

It is a **blueprint for how future AI systems will be built.**
