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
- Python 3.12+
- OpenRouter API key
- uv package manager
- Bindu installed in project root

### 1. Set Environment Variables

Create `.env` file in `examples/cerina_bindu/cbt/` with only:

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 2. Install Dependencies

```bash
# From Bindu root directory
uv sync
```

### 3. Start the CBT Supervisor

```bash
# From Bindu root directory
cd examples/cerina_bindu/cbt
uv run python supervisor_cbt.py
```

The agent will start on `http://localhost:3773`

### 4. Send a Message

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
        "parts": [{"kind": "text", "text": "I am overwhelmed with sleep problems"}],
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

- **`supervisor_cbt.py`** - Main Bindu agent handler with `@bindufy` decorator
- **`langgraph_integration.py`** - Adapter that initializes and invokes the LangGraph workflow
- **`state_mapper.py`** - Bidirectional mapping between ProtocolState and Bindu artifact format
- **`agents.py`** - Three specialized agent implementations (Drafter, SafetyGuardian, ClinicalCritic)
- **`workflow.py`** - LangGraph workflow orchestration logic with node definitions
- **`state.py`** - ProtocolState schema and state management utilities
- **`utils.py`** - Helper functions for logging and error handling
- **`database.py`** - Database models for session persistence (optional)
- **`skills/cbt-therapy-skill/`** - Bindu skill definition and metadata

### State Management

- Each invocation runs the workflow from scratch (stateless)
- Bindu `context_id` is tracked for logging purposes only
- No state persistence between invocations

## How It Works

### Message Flow

1. **Bindu receives message** → `supervisor_cbt.handler()` via `@bindufy` decorator
2. **Extract user intent** from message parts using `state_mapper.extract_text_from_bindu_message()`
3. **Map to LangGraph input** using `state_mapper.build_langgraph_input()`
4. **Invoke workflow** via `LangGraphWorkflowAdapter.invoke()`
5. **Multi-agent processing** through Drafter → Safety Guardian → Clinical Critic
6. **Map output** to Bindu artifact format using `state_mapper.protocol_state_to_bindu_artifact()`
7. **Return response** as structured Bindu artifact with safety scores

### Agent Roles

| Agent | Role | Output |
|-------|------|--------|
| **Drafter** | Generates initial CBT exercise draft | `current_draft` |
| **SafetyGuardian** | Validates clinical safety & ethics | `safety_verdict`, `safety_score` (0-100) |
| **ClinicalCritic** | Reviews therapeutic quality | `clinical_critique`, `clinical_score` (0-100) |

### Model Configuration

- **Provider**: OpenRouter
- **Model**: `openai/gpt-oss-120b`
- **Temperature**: 0.7 (balanced creativity and consistency)
- **API**: Uses OpenRouter's API endpoint

## Skills Integration

The CBT agent includes a Bindu skill definition in `skills/cbt-therapy-skill/`:

- **Skill ID**: `cbt-therapy-skill`
- **Capabilities**: CBT protocol generation, safety validation, quality assessment
- **Input/Output**: JSON format for structured data exchange
- **Tags**: therapy, mental-health, cbt, wellness, self-help

## Background

This example is based on [Cerina Protocol Foundry](https://github.com/Danish137/cerina-protocol-foundry),
a research project for generating therapeutic CBT protocols using multi-agent LLM orchestration.

**For this Bindu integration**, the design has been optimized:
- **Removed**: SQLite persistence (one-shot invocation for privacy)
- **Removed**: Async checkpointers (stateless execution)
- **Removed**: MCP servers and RPC layer (direct LangGraph invocation)
- **Added**: Bindu protocol compliance with `@bindufy` decorator
- **Added**: OpenRouter integration with `openai/gpt-oss-120b`
- **Added**: Skills folder with proper Bindu skill definition
- **Kept**: Core multi-agent orchestration logic (Drafter → Safety → Critic)

This makes the example lightweight, secure, and easy to integrate while preserving the sophisticated agent workflow.

## Dependencies

All dependencies are managed through the root `pyproject.toml`:

```bash
# Core dependencies already included in bindu project
langchain>=1.2.9
langchain-openai>=1.1.8
langgraph>=1.0.8
python-dotenv>=1.1.0
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
