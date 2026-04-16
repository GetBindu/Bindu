# Bindu - Project Context Documentation

## Overview

**Bindu** (pronounced "binduu") is an open-source framework that transforms any AI agent into a production microservice with built-in identity, communication, and payment capabilities. It acts as "the identity, communication & payments layer for AI agents."

### Mission
Build the "Internet of Agents" - where agents can discover, communicate, negotiate, and transact with each other autonomously using open protocols.

---

## What Bindu Does

Bindu takes any AI agent (built with Agno, LangChain, CrewAI, OpenAI SDK, etc.) and adds:

1. **Decentralized Identity (DID)** - Cryptographic identity for every agent
2. **A2A Protocol** - Agent-to-Agent communication standard
3. **AP2 Protocol** - Agentic commerce protocol
4. **X402 Payments** - USDC payments on Base blockchain before executing protected methods
5. **OAuth2 Authentication** - Secure API access via Ory Hydra
6. **Skills System** - Reusable capabilities that agents can advertise/discover
7. **Task Scheduling** - Redis or in-memory async task management
8. **Persistent Storage** - PostgreSQL or in-memory storage
9. **Observability** - OpenTelemetry + Sentry integration

---

## Project Structure

```
Bindu/
├── bindu/                    # Main Python package
│   ├── penguin/              # Core agent binding (bindufy)
│   │   ├── bindufy.py        # Main entry point - transforms agents to services
│   │   ├── config_validator.py
│   │   ├── did_setup.py
│   │   └── manifest.py
│   ├── server/               # HTTP/gRPC server implementation
│   │   ├── applications.py   # Main Starlette/FastAPI app
│   │   ├── endpoints/        # HTTP endpoints
│   │   │   ├── a2a_protocol.py
│   │   │   ├── agent_card.py
│   │   │   ├── negotiation.py
│   │   │   ├── payment_sessions.py
│   │   │   └── skills.py
│   │   ├── handlers/         # Request handlers
│   │   ├── middleware/       # HTTP middleware
│   │   ├── scheduler/        # Task scheduling
│   │   ├── storage/          # Database storage
│   │   └── workers/          # Background workers
│   ├── grpc/                 # gRPC service definitions
│   │   ├── client.py         # gRPC client
│   │   ├── server.py         # gRPC server
│   │   ├── service.py        # Service implementation
│   │   └── registry.py       # Agent registry
│   ├── auth/                 # Authentication (OAuth2/Hydra)
│   ├── tunneling/            # FRP tunnel for exposing local agents
│   ├── extensions/           # Agent extensions (DID, X402)
│   ├── common/               # Common models
│   │   └── protocol/         # A2A protocol types
│   ├── utils/                # Utilities
│   ├── observability/        # OpenTelemetry instrumentation
│   └── settings.py           # Configuration settings
├── frontend/                 # React/Svelte web UI (port 5173)
├── examples/                 # Example agents
│   ├── beginner/             # Beginner examples
│   ├── ag2_research_team/    # AG2 example
│   ├── agent_swarm/          # Multi-agent swarm
│   ├── typescript-openai-agent/  # TypeScript SDK example
│   ├── kotlin-openai-agent/  # Kotlin SDK example
│   └── skills/               # Reusable skills
├── proto/                    # gRPC protocol definitions
│   └── agent_handler.proto
├── sdks/                     # Language-specific SDKs
│   ├── typescript/           # TypeScript SDK (@bindu/sdk)
│   └── kotlin/               # Kotlin SDK
├── docs/                     # Documentation
├── alembic/                  # Database migrations
└── tests/                    # Test suite
```

---

## Key Technologies & Dependencies

### Core
- **Python 3.12+** - Minimum version
- **uvicorn** - ASGI server
- **starlette** - Web framework
- **pydantic** - Data validation
- **loguru** - Logging

### Identity & Security
- **cryptography** - Cryptographic operations
- **pynacl** - NaCl cryptography
- **pyjwt** - JWT handling
- **base58** - Base58 encoding for DIDs

### Database & Cache
- **sqlalchemy** + **asyncpg** - PostgreSQL async
- **redis** - Task queue/scheduler
- **alembic** - Migrations

### Payments (X402)
- **x402** - Payment protocol
- **web3** - Ethereum/Base blockchain
- **eth-account** - Ethereum accounts
- **cdp-sdk** - Coinbase Developer Platform

### Observability
- **opentelemetry-api/sdk** - Tracing
- **sentry-sdk** - Error tracking

### Agent Frameworks (Optional)
- agno, ag2, langchain, langgraph, crewai, llamaindex

---

## Architecture Overview

### The `bindufy()` Function

This is the main entry point. It transforms a regular agent handler function into a full microservice:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    # Your agent logic
    return response

config = {
    "author": "you@example.com",
    "name": "my_agent",
    "description": "My agent",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
    },
    "skills": ["skills/pdf-processing"]
}

bindufy(config, handler)
```

### What happens inside `bindufy()`:

1. **Config Validation** - Validate and process agent configuration
2. **DID Generation** - Create decentralized identity (Ed25519 keys)
3. **Manifest Creation** - Generate A2A agent card with capabilities
4. **Server Startup** - Start uvicorn HTTP server (port 3773)
5. **Endpoint Registration** - Register A2A, DID, skills, payment endpoints
6. **Tunnel Setup** (optional) - Expose via FRP tunnel
7. **Storage/Scheduler Init** - PostgreSQL/Redis or in-memory defaults

### Communication Flow

```
Client -> HTTP Server (3773) -> A2A Protocol Handler -> Task Manager
                                                        |
                                                        v
                                                    Agent Handler
                                                        |
                                                        v
                                                    Response
```

### gRPC Language Agnostic Support

Bindu supports agents in other languages via gRPC:

1. **TypeScript SDK** calls `BinduService.RegisterAgent()` on Python core
2. Core runs full bindufy (DID, auth, manifest)
3. When task arrives, core calls `AgentHandler.HandleMessages()` on SDK
4. SDK executes user's handler and returns response

---

## Core Concepts

### Agent Identity (DID)

Every Bindu agent gets a W3C Decentralized Identifier:
```
did:key:z6MkhaXgBZNv2q7W5U9U7LwP4f7q3Xk8y2z1w5u8t3r6e9i0
```

This is used for:
- Verifiable identity without central authority
- Message signing/verification
- Payment attribution

### A2A Protocol

The Agent-to-Agent protocol defines:
- `message/send` - Send messages to agent
- `tasks/get` - Get task status
- `tasks/cancel` - Cancel task
- `tasks/pushNotify/set` - Set up webhooks

### Skills System

Skills are reusable capabilities that agents advertise:
- Stored in `skills/` directory
- Defined in `skill.yaml` with name, description, handlers
- Used for intelligent task routing between agents

### X402 Payments

For monetized agents:
- USDC payments on Base blockchain
- Payment required before protected method execution
- Supports multiple payment options

---

## Configuration

### Environment Variables

Key settings via env vars:
- `BINDU_PORT` - Server port (default: 3773)
- `BINDU_DEPLOYMENT_URL` - Override deployment URL
- `OPENROUTER_API_KEY` / `OPENAI_API_KEY` - LLM providers
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- Auth, Vault, Sentry configs via prefix (e.g., `AUTH__`, `SENTRY__`)

### Settings Module

Located at `bindu/settings.py`:
- `ProjectSettings` - Environment, name, version
- `DIDSettings` - DID method, key paths, resolver
- `NetworkSettings` - Host, port, timeouts
- `TunnelSettings` - FRP configuration
- `AuthSettings` - OAuth2/Hydra config
- `StorageSettings` - Database config
- `SchedulerSettings` - Redis config

---

## Supported Frameworks

### Python
- AG2 (formerly AutoGen)
- Agno
- CrewAI
- LangChain
- LangGraph
- LlamaIndex
- FastAgent

### TypeScript
- OpenAI SDK
- LangChain.js

### Kotlin
- OpenAI Kotlin SDK

### Any Language (via gRPC)
- Rust, Go, C++, etc.

---

## Running Bindu

### Install
```bash
uv add bindu
```

### Run an Agent
```bash
python examples/echo_agent.py
# Agent available at http://localhost:3773
```

### Run Chat UI
```bash
cd frontend && npm run dev
# UI available at http://localhost:5173
```

### Test Agent
```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send",...}'
```

---

## Testing

```bash
# Unit tests
uv run pytest tests/unit/ -v

# E2E gRPC tests
uv run pytest tests/integration/grpc/ -v -m e2e

# Coverage
uv run pytest -n auto --cov=bindu --cov-report=term-missing
```

Target: 70%+ code coverage

---

## Development

### Setup
```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

### Pre-commit Hooks
- Ruff linting
- Type checking
- Secret detection
- File formatting

---

## Roadmap

- [x] gRPC transport + language-agnostic SDKs (TypeScript, Kotlin)
- [ ] Increase test coverage to 80%
- [ ] AP2 end-to-end support
- [ ] DSPy integration (in progress)
- [ ] Rust SDK
- [ ] MLTS support
- [ ] X402 support with other facilitators

---

## Community

- **Discord**: https://discord.gg/3w5zuYUuwt
- **Documentation**: https://docs.getbindu.com
- **Website**: https://getbindu.com

---

## License

Apache 2.0 - see LICENSE.md

---

## Maintainers

- **Raahul Dutta** - Lead maintainer, founder

See maintainers.md for contribution process and becoming a maintainer.

---

## Acknowledgements

- FastA2A
- A2A Protocol
- AP2 (Google Agentic Commerce)
- X402 (Coinbase)
- HuggingFace chat-ui
- 12 Factor Agents

---

## Vision

> "Like sunflowers turning toward the light, agents collaborate in swarms - each one independent, yet together they create something greater."

Bindu aims to be the "dot" (bindu in Sanskrit) - the origin point that connects all agents in the Internet of Agents.