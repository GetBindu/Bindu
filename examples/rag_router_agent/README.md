# 🌻 RAG Router Agent (Bindu)

## 🚀 Overview

A Bindu-native agent that performs Retrieval-Augmented Generation (RAG) with **intent-based routing** across multiple knowledge sources.

## 🧠 Features

* Intent classification (finance, legal, tech)
* Dynamic database routing
* Context retrieval (top-k)
* LLM-based answer generation
* Structured response output (`answer`, `intent`, `db_used`)

## ⚙️ How it works

User Query → Intent Detection → DB Routing → Retrieval → LLM Response

## 🧪 Example

**Query:**
`What is GST?`

**Response:**

```json
{
  "answer": "GST is a tax applied on goods and services...",
  "intent": "finance",
  "db_used": "db/finance.txt"
}
```

## ▶️ Run Locally

```bash
cd examples/rag_router_agent
python test_local.py
```

> Requires: `OPENROUTER_API_KEY`

## 💡 Why this matters

This agent demonstrates how Bindu agents can:

* Understand intent before acting
* Route tasks efficiently instead of brute-force retrieval
* Act as coordination layers in multi-agent systems

## 🔌 Bindu Integration

* Built using `bindufy()`
* Exposed via JSON-RPC (A2A protocol)
* Runs as a lightweight agent microservice

## 🔥 Future Scope

* Agent-to-agent routing (A2A)
* Vector database integration (FAISS/Chroma)
* Confidence-based hybrid routing
