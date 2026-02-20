# Collaborative Multi-Agent Research System

## Overview

This module implements a collaborative multi-agent system built using Bindu. It demonstrates how multiple AI agents can work together to solve a research task through information retrieval, processing, validation, and iterative refinement.

The system follows a structured pipeline:

User Query → Search Agent → Summary Agent → Verifier Agent → Feedback Loop → Final Output

This implementation focuses on agent collaboration, tool usage, and self-improvement using feedback.

---

## Architecture

The system consists of three core agents:

### 1. Search Agent

* Retrieves real-time information from the web using DDGS (DuckDuckGo Search)
* Returns structured results including title, snippet, and source link
* Includes retry logic for robustness

### 2. Summary Agent

* Processes raw search results
* Generates concise summaries in structured bullet points
* Focuses on extracting key insights

### 3. Verifier Agent

* Evaluates the generated summary
* Checks for:

  * Accuracy
  * Completeness
  * Hallucination
* Returns structured output with status and feedback

---

## Agent Collaboration

The system implements a feedback-driven collaboration loop:

1. The Summary Agent generates an initial summary
2. The Verifier Agent evaluates the summary
3. If the summary is marked INVALID:

   * Feedback is passed back to the system
   * The summary is improved using the feedback
4. The improved summary is re-evaluated

This demonstrates agent-to-agent interaction and iterative refinement, aligning with the concept of collaborative AI systems.

---

## Features

* Multi-agent architecture
* Tool-using agent (web search via DDGS)
* Local LLM integration using Ollama (cost-efficient, replaceable with APIs)
* Feedback-driven improvement loop
* Retry mechanism for reliability
* Modular and extensible design
* Execution time tracking for each agent

---

## Project Structure

```text
examples/multi_agent_research/
│
├── agents/
│   ├── search_agent.py
│   ├── summary_agent.py
│   └── verifier_agent.py
│
├── utils/
│   └── llm.py
│
├── workflow/
│   └── graph.py
│
└── main.py
```

---

## How It Works

### Step 1: Search

The Search Agent retrieves relevant information from the web using DDGS.

### Step 2: Summarization

The Summary Agent processes the retrieved content and produces structured bullet points.

### Step 3: Verification

The Verifier Agent evaluates the summary for correctness and completeness.

### Step 4: Improvement (if required)

If the summary is marked INVALID:

* Feedback is used to refine the summary
* The system regenerates an improved version
* The improved output is re-validated

---

## Model Configuration

This project uses a local LLM via Ollama for development.

### Why Ollama?

During development, a local model (Ollama) was used instead of API-based models to:

- Avoid API costs while iterating on agent logic
- Enable offline experimentation
- Allow faster development without external dependencies

This ensures that the focus remains on building the agent architecture, tool integration, and collaboration logic rather than managing API usage.

### Production Consideration

In a production environment, this setup can be easily replaced with hosted LLM providers such as:

- OpenAI API
- OpenRouter
- Other LLM services

The system is designed to be model-agnostic. Switching to an API-based model only requires updating the LLM interface in `utils/llm.py`, without changing the agent logic.

This separation ensures scalability and flexibility across different deployment environments.

### Why Ollama?

* Avoids API usage costs during development
* Enables offline experimentation
* Allows rapid iteration without external dependencies

### Production Setup

In production, the model can be replaced with API-based providers such as:

* OpenAI API
* OpenRouter
* Other LLM services

The system is designed to be model-agnostic. Switching to an API-based model only requires updating the LLM interface in `utils/llm.py`.

---

## Requirements

* Python 3.12+
* Ollama installed and running locally
* LLM model (e.g., llama3)

Ensure Ollama is running at:

```
http://localhost:11434
```

---

## Installation

Install required dependency for search:

```bash
uv add ddgs
```

---

## Running the System

Run the module:

```bash
python -m examples.multi_agent_research.main
```

Enter a query when prompted.

Example:

```
Latest developments in LLMs
```

---

## Example Flow

1. Search Agent retrieves web data
2. Summary Agent generates structured summary
3. Verifier Agent evaluates the output
4. If needed, summary is improved using feedback
5. Final validated result is displayed

---

## Limitations

* Depends on local LLM performance (Ollama)
* Search results depend on external sources
* No persistent memory between runs
* Sequential execution (no parallel agents)

---

## Future Improvements

* Integration with LangGraph for advanced orchestration
* Parallel agent execution
* Memory and context retention
* API interface (FastAPI)
* Additional tool integrations

---

## Motivation

This project aligns with Bindu’s vision of building interoperable AI agents that can:

* Communicate
* Collaborate
* Validate outputs
* Improve iteratively

It demonstrates how agents can move beyond simple execution into coordinated, feedback-driven systems.

---

## Summary

This module showcases a collaborative multi-agent system where agents:

* Use tools to gather information
* Process data using LLMs
* Validate and refine outputs through feedback loops

It highlights the transition from single-agent systems to collaborative agent ecosystems.
