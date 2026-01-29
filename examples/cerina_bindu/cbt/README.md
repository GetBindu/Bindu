# Cerina CBT Integration with Bindu

A production-ready Cognitive Behavioral Therapy (CBT) agent system integrated with Bindu. This example demonstrates how to integrate a complex multi-agent LangGraph workflow into Bindu's orchestration framework.

## What is This?

This is a **fully functional CBT protocol generation system** that:
- Takes a user concern/statement and generates a personalized CBT exercise in a single invocation
- Routes requests through a multi-agent LangGraph workflow
- Integrates seamlessly with Bindu's agent framework

### Workflow

```
User Message (Bindu format)
    ↓
Bindu Supervisor Agent (supervisor_cbt.py)
    ↓ [maps context_id → LangGraph thread_id]
Multi-Agent Workflow
    ├─→ Drafter Agent: Creates initial protocol draft
    ├─→ Safety Guardian: Validates clinical safety
    └─→ Clinical Critic: Ensures therapeutic quality
    ↓ [ProtocolState]
State Mapper: Converts to Bindu artifact format
    ↓
Structured CBT Response
```

## Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key (or ChatAnywhere proxy)
- Bindu running locally

### 1. Set Environment Variables

Create `.env` file in `examples/cerina_bindu/cbt/`:

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key

### 2. Start the CBT Supervisor

```bash
# From Bindu root directory
python examples/cerina_bindu/cbt/supervisor_cbt.py
```

The agent will start on `http://localhost:3773`

### 3. Send a Message

Open your browser to `http://localhost:3773/docs` and use the chat interface, or:

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "I am overwhelmed with sleep"}],
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

## Architecture

### File Structure

- **`supervisor_cbt.py`** - Bindu agent handler that accepts Bindu messages
- **`langgraph_integration.py`** - Adapter that initializes and invokes the LangGraph workflow
- **`state_mapper.py`** - Bidirectional mapping between ProtocolState and Bindu artifact format
- **`agents.py`** - Three agent implementations (Drafter, SafetyGuardian, ClinicalCritic)
- **`workflow.py`** - LangGraph workflow orchestration logic
- **`state.py`** - ProtocolState schema and utilities
- **`utils.py`** - Helper functions for logging and state management

### State Management

- Each invocation runs the workflow from scratch (stateless)
- Bindu `context_id` is tracked for logging purposes only
- No state persistence between invocations

## How It Works

### Message Flow

1. **Bindu receives message** → `supervisor_cbt.handler()`
2. **Extract user intent** from message parts
3. **Map to LangGraph input** using `state_mapper.build_langgraph_input()`
4. **Invoke workflow** via `LangGraphWorkflowAdapter.invoke()`
5. **Map output** to Bindu artifact format using `state_mapper.protocol_state_to_bindu_artifact()`
6. **Return response** as structured Bindu artifact

### Agent Roles

| Agent | Role | Output |
|-------|------|--------|
| **Drafter** | Generates initial CBT exercise draft | `current_draft` |
| **SafetyGuardian** | Validates clinical safety & ethics | `safety_verdict`, `safety_score` |
| **ClinicalCritic** | Reviews therapeutic quality | `clinical_critique`, `clinical_score` |

## Background

## Background

This example is based on [Cerina Protocol Foundry](https://github.com/Danish137/cerina-protocol-foundry), 
a research project for generating therapeutic CBT protocols using multi-agent LLM orchestration. 

**For this Bindu integration**, the design has been simplified:
- **Removed**: SQLite persistence (one-shot invocation, no multi-turn state)
- **Removed**: Async checkpointers (stateless execution)
- **Removed**: MCP servers and RPC layer (direct LangGraph invocation)
- **Kept**: Core multi-agent orchestration logic (Drafter → Safety → Critic)

This makes the example lightweight and easy to integrate while preserving the sophisticated agent workflow.

## Dependencies

Create a `requirements.txt` in the `cerina_bindu/cbt/` folder:

```
langchain>=0.3.0
langchain-openai>=0.2.0
langgraph>=0.2.0
python-dotenv>=1.0.0
```

Or install directly:
```bash
pip install langchain langchain-openai langgraph python-dotenv
```


## Integration Details
.parts[0].text → user_intent (input to workflow)
├─ contextId → session tracking (for logs)
├─ messageId → task tracking
└─ taskId → metadata tracking

↓ (via state_mapper)

LangGraph Input State
├─ user_intent: str (user's concern)
├─ session_id: str (from contextId)
├─ metadata: dict (task info)
└─ max_iterations: 3 (fixed for quality)
LangGraph Input State
├─ user_intent: str
├─ session_id: str (from contextId)
├─ metadata: dict (task info)
└─ max_iterations: int
```

### How ProtocolState Maps to Bindu Artifact

```python
ProtocolState (after 3 agents have processed)
├─ current_draft → artifact body (final CBT exercise)
├─ safety_verdict → artifact metadata (is it safe?)
├─ safety_score → artifact metadata (0-100)
├─ clinical_critique → artifact metadata (quality feedback)
└─ clinical_score → artifact metadata (0-100)

↓ (via state_mapper)

Bindu Artifact (one-time response)
├─ kind: "artifact"
├─ mimeType: "application/json"
├─ body: (complete CBT exercise ready to use)
└─ metadata: (safety & clinical scores, feedback)
```

## Contributing

To extend or modify this example:

1. Edit agent prompts in `agents.py`
2. Modify workflow logic in `workflow.py`
3. Add new state fields in `state.py`
4. Update mappers in `state_mapper.py`

