# Cerina Bindu

A production-ready **Cognitive Behavioral Therapy (CBT) agent system** built on the Bindu framework using LangGraph multi-agent orchestration.

This example demonstrates how to integrate a complex multi-agent workflow into Bindu — showing that `bindufy()` works with sophisticated, production-grade agent architectures, not just simple single-agent setups.

---

## What It Does

Takes a user concern and generates a personalized CBT exercise through a three-agent pipeline:

```
User concern
     ↓
Drafter Agent → creates initial CBT protocol
     ↓
Safety Guardian → validates clinical safety (0-100 score)
     ↓
Clinical Critic → ensures therapeutic quality (0-100 score)
     ↓
Structured CBT response with safety + quality scores
```

---

## Contents

```
cerina_bindu/
└── cbt/                          — Main CBT agent implementation
    ├── supervisor_cbt.py         — Bindu entry point (@bindufy decorator)
    ├── agents.py                 — Three agent implementations
    ├── workflow.py               — LangGraph workflow orchestration
    ├── langgraph_integration.py  — LangGraph ↔ Bindu adapter
    ├── state_mapper.py           — State ↔ Bindu artifact mapping
    ├── state.py                  — ProtocolState schema
    ├── utils.py                  — Helper functions
    ├── database.py               — Optional session persistence
    ├── skills/                   — Bindu skill definition
    └── README.md                 — Full setup and usage guide
```

---

## Quick Start

```bash
# From Bindu root directory
cd examples/cerina_bindu/cbt

# Set your API key
cp .env.example .env
# Add OPENROUTER_API_KEY to .env

# Run the agent
uv run python supervisor_cbt.py
```

Agent starts at `http://localhost:3773`. See [`cbt/README.md`](cbt/README.md) for full usage instructions including example curl commands.

---

## What This Demonstrates

- **Complex workflow bindufying** — a full LangGraph multi-agent pipeline wrapped in a single `bindufy()` call
- **Framework agnostic** — LangGraph + Bindu working together seamlessly
- **Production patterns** — safety validation, quality scoring, structured artifact output
- **Skill integration** — custom Bindu skill definition for CBT therapy

---

## Background

Based on [Cerina Protocol Foundry](https://github.com/Danish137/cerina-protocol-foundry) — a research project for generating therapeutic CBT protocols using multi-agent LLM orchestration.

---

## Related Examples

- [`examples/collaborative-agents/`](../collaborative-agents/) — multi-agent A2A communication
- [`examples/agent_swarm/`](../agent_swarm/) — agent swarm patterns
- [`examples/beginner/`](../beginner/) — simple single-agent examples
