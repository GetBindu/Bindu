# Project: Bindu - Decentralized Agent Framework

## Critical Context (Read First)

- **Language**: Python 3.12+ (core), TypeScript (SDK + frontend)
- **Framework**: FastAPI/Starlette (HTTP), gRPC (cross-language), SvelteKit (frontend)
- **Database**: MongoDB (primary), PostgreSQL (optional), Redis (caching)
- **Architecture**: Microservices with DID-based identity, OAuth2 auth, x402 payments
- **Testing**: pytest (Python), Jest (TypeScript), Playwright (E2E)

## What is Bindu?

Bindu is a framework for building **autonomous AI agents as microservices**. Each agent:
- Has a DID (Decentralized Identifier) for cryptographic identity
- Speaks the A2A (Agent-to-Agent) protocol over HTTP
- Can be written in any language via gRPC SDKs
- Supports payments via x402 protocol (USDC on Base)
- Integrates with OAuth2 (Ory Hydra) for authentication

## Commands That Work

```bash
# Python core development
uv sync                          # Install dependencies
uv run pytest                    # Run all tests
uv run pytest tests/unit         # Unit tests only
uv run pytest tests/integration  # Integration tests only
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run mypy bindu                # Type check

# Start the core
bindu serve --grpc               # Start with gRPC server (for SDKs)
python -m bindu.cli serve --grpc # Alternative

# TypeScript SDK
cd sdks/typescript
npm install
npm run build                    # Compile TypeScript
npm test                         # Run tests
npm run lint                     # ESLint

# Frontend
cd frontend
npm install
npm run dev                      # Dev server (port 5173)
npm run build                    # Production build
npm run preview                  # Preview build

# Examples
cd examples/typescript-openai-agent
npm install
cp .env.example .env             # Configure API keys
npx tsx index.ts                 # Run agent
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Bindu Core (Python)                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ HTTP Server  │  │ gRPC Server  │  │ Task System  │      │
│  │ :3773 (A2A)  │  │ :3774 (SDK)  │  │ Scheduler    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ DID System (Ed25519) | OAuth2 (Hydra) | x402 (USDC) │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ gRPC
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                  Language SDKs (Thin Wrappers)              │
│                                                             │
│  TypeScript SDK  │  Kotlin SDK (planned)  │  Rust (planned)│
│  @bindu/sdk      │                        │                │
└─────────────────────────────────────────────────────────────┘
```

## Important Patterns

### Python Core

- **Agent creation**: Use `bindufy(config, handler)` in `bindu/core.py`
- **DID management**: `bindu/did/` - Ed25519 keys, DID documents, verification
- **Task execution**: `ManifestWorker` in `bindu/manifest_worker.py` - handles all task lifecycle
- **Storage**: `bindu/storage/` - MongoDB for tasks/messages, file storage for artifacts
- **Extensions**: `bindu/extensions/` - DID, x402, auth, skills
- **gRPC**: `bindu/grpc/` - BinduService (SDK→Core), GrpcAgentClient (Core→SDK)

### TypeScript SDK

- **Entry point**: `bindufy(config, handler)` in `sdks/typescript/src/index.ts`
- **Handler signature**: `async (messages: ChatMessage[]) => Promise<string | HandlerResponse>`
- **gRPC server**: `AgentHandler` service in `src/server.ts` receives HandleMessages calls
- **gRPC client**: Calls `RegisterAgent` on core in `src/client.ts`
- **Core launcher**: `src/core-launcher.ts` spawns Python core as child process

### A2A Protocol (HTTP JSON-RPC)

All agents expose these endpoints on port 3773:
- `POST /` - JSON-RPC 2.0 endpoint
  - `message/send` - Send a message to the agent
  - `message/stream` - Stream messages (not yet implemented for gRPC agents)
- `GET /.well-known/agent.json` - Agent card (DID, capabilities, skills)
- `GET /.well-known/did.json` - DID document
- `GET /health` - Health check

### Response Contract

Handlers return:
- **String**: Task completes immediately with this response
- **Dict with `state`**: Task transitions to new state
  - `{"state": "input-required", "prompt": "..."}` - Needs more info
  - `{"state": "auth-required"}` - Needs authentication
  - `{"state": "payment-required"}` - Needs payment

## File Structure

```
bindu/
├── bindu/                      # Python core
│   ├── core.py                 # bindufy() entry point
│   ├── manifest_worker.py      # Task execution engine
│   ├── did/                    # DID system
│   ├── grpc/                   # gRPC services
│   │   ├── server.py           # BinduService (SDK→Core)
│   │   ├── client.py           # GrpcAgentClient (Core→SDK)
│   │   └── registry.py         # Agent registry
│   ├── storage/                # MongoDB, file storage
│   ├── extensions/             # DID, x402, auth, skills
│   ├── ui/                     # HTTP server (Starlette)
│   └── cli/                    # CLI (bindu serve --grpc)
├── sdks/
│   └── typescript/             # TypeScript SDK
│       ├── src/
│       │   ├── index.ts        # bindufy() function
│       │   ├── server.ts       # AgentHandler gRPC server
│       │   ├── client.ts       # BinduService gRPC client
│       │   └── core-launcher.ts # Spawns Python core
│       └── proto/              # gRPC proto files
├── frontend/                   # SvelteKit UI
│   └── src/
│       ├── routes/             # Pages
│       └── lib/                # Components, utilities
├── examples/
│   ├── typescript-openai-agent/
│   └── typescript-langchain-agent/
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── docs/                       # Documentation
│   ├── grpc/                   # gRPC docs (overview, API, SDKs)
│   └── MTLS_DEPLOYMENT_GUIDE.md
└── proto/                      # gRPC proto definitions
    └── agent_handler.proto     # Single source of truth
```

## Gotchas & What NOT to Do

### Python Core

- **DON'T** modify `bindu/grpc/generated/` - auto-generated from proto
- **DON'T** use `del dict[key]` - use `dict.pop(key, None)` for optional keys
- **DON'T** commit `.env` files - use `.env.example` templates
- **ALWAYS** run `uv sync` after pulling dependency changes
- **ALWAYS** use `app_settings` from `bindu/settings.py` for config, not env vars directly
- **DON'T** call `manifest.run()` directly - use `ManifestWorker` for task execution
- **ALWAYS** use `get_logger(__name__)` from `bindu/utils/logging.py`, not `print()`

### TypeScript SDK

- **DON'T** modify `src/generated/` - auto-generated from proto
- **DON'T** hardcode ports - use config or auto-assign (port 0)
- **ALWAYS** kill the Python child process on exit
- **ALWAYS** send heartbeats every 30 seconds after registration
- **DON'T** return incomplete responses - streaming not yet implemented

### gRPC

- **DON'T** change `proto/agent_handler.proto` without regenerating stubs
- **ALWAYS** regenerate both Python and TypeScript stubs after proto changes:
  ```bash
  # Python
  python -m grpc_tools.protoc -I proto --python_out=bindu/grpc/generated --grpc_python_out=bindu/grpc/generated proto/agent_handler.proto

  # TypeScript
  cd sdks/typescript
  npm run generate-proto
  ```
- **DON'T** use `HandleMessagesStream` - not implemented yet (see docs/grpc/limitations.md)

### Testing

- **ALWAYS** use fixtures from `tests/conftest.py`
- **DON'T** use real MongoDB in unit tests - use `mongodb-memory-server` or mocks
- **ALWAYS** clean up test data in teardown
- **DON'T** skip tests without a good reason and a TODO comment

## Recent Learnings

- **[2026-03-25]** Pre-commit secrets detection: Add `# pragma: allowlist secret` to `.env.example` files to suppress false positives
- **[2026-03-24]** Agent trust validation: New `AgentTrustConfig` in `types.py` with 10 trust levels (PR #399)
- **[2026-03-29]** Payment context handling: Use `.pop()` instead of `del` for optional metadata keys (PR #418)
- **[2026-03-29]** Windows compatibility: DID private key permissions - use `os.open()` on POSIX, direct write on Windows (PR #418)
- **[2026-03-27]** gRPC docs reorganized: See `docs/grpc/` for architecture, API reference, SDK guides
- **[2026-04-20]** Gateway recipes: progressive-disclosure playbooks the planner lazy-loads on demand. Live in `gateway/recipes/` as markdown files with YAML frontmatter. Metadata (name + description) goes into the system prompt; full body only loads when the planner calls `load_recipe`. Pattern ported from OpenCode skills, renamed because the gateway already uses "skill" for A2A agent capabilities. See `gateway/src/recipe/index.ts` and `gateway/README.md` §Recipes.

## Key Design Decisions

### Why gRPC for SDKs?

- **Bidirectional**: Both core and SDK can initiate calls
- **Typed**: Proto definitions are single source of truth
- **Cross-language**: Works with any language that has gRPC support
- **Performance**: Binary protocol, faster than JSON over HTTP

### Why Two Processes (Core + SDK)?

- **Avoid reimplementation**: Don't rewrite DID, auth, x402, scheduler in every language
- **Thin SDKs**: ~300 lines of code per language
- **One codebase**: All infrastructure logic in Python
- **Developer UX**: They only see their language, Python is invisible

### Why ManifestWorker?

- **Separation of concerns**: Task lifecycle separate from handler logic
- **State machine**: Handles all task states (pending, running, completed, failed, input-required, etc.)
- **Uniform interface**: `manifest.run(messages)` works for Python and gRPC handlers identically
- **Error handling**: Catches exceptions, creates artifacts, updates storage

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Mock external dependencies (MongoDB, Redis, HTTP clients)
- Test individual functions and classes in isolation
- Fast (<1s per test)

### Integration Tests (`tests/integration/`)
- Use real MongoDB (memory server) and Redis
- Test component interactions (e.g., gRPC client ↔ server)
- Medium speed (1-5s per test)

### E2E Tests (`tests/e2e/`)
- Full agent lifecycle: register → execute → verify
- Real HTTP requests, real gRPC calls
- Slow (5-30s per test)

## Security Model

### Layer 1: Transport (mTLS) - PLANNED
- X.509 certificates from Smallstep step-ca
- Mutual authentication between agents
- See `docs/MTLS_DEPLOYMENT_GUIDE.md`

### Layer 2: Application (OAuth2) - IMPLEMENTED
- Ory Hydra for OAuth2/OIDC
- JWT tokens for API authorization
- Scopes: `agent:read`, `agent:write`, `agent:execute`

### Layer 3: Message (DID Signatures) - IMPLEMENTED
- Ed25519 signatures on all artifacts
- DID verification via `did:bindu:` method
- Prevents message tampering

### Layer 4: Payment (x402) - IMPLEMENTED
- USDC payments on Base (Sepolia testnet)
- Coinbase Commerce integration
- Pay-per-execution model

## Common Workflows

### Adding a New Feature to Python Core

1. Write tests first (`tests/unit/` or `tests/integration/`)
2. Implement the feature
3. Run tests: `uv run pytest`
4. Update docs if needed
5. Commit with descriptive message

### Building a New Language SDK

1. Read `docs/grpc/sdk-development.md`
2. Generate gRPC stubs from `proto/agent_handler.proto`
3. Implement `AgentHandler` service (receives HandleMessages)
4. Implement `BinduService` client (calls RegisterAgent)
5. Implement core launcher (spawns `bindu serve --grpc`)
6. Expose `bindufy(config, handler)` function
7. Test with E2E example

### Debugging gRPC Issues

1. Check core logs: `[bindu-core]` prefix in terminal
2. Check SDK logs: Usually prefixed with SDK name
3. Test with `grpcurl`:
   ```bash
   grpcurl -plaintext -proto proto/agent_handler.proto localhost:3774 list
   grpcurl -plaintext -proto proto/agent_handler.proto -d '{"agent_id":"test","timestamp":1234567890}' localhost:3774 bindu.grpc.BinduService.Heartbeat
   ```
4. Check ports: `lsof -ti:3773 -ti:3774`
5. Read `docs/grpc/limitations.md` for known issues

### Reviewing PRs

1. Check PR description matches actual changes
2. Verify tests pass and new tests added
3. Look for scope creep (unrelated changes)
4. Check for broken/incomplete code
5. Verify backward compatibility
6. Check error handling (no raw exceptions to users)
7. Ensure docs updated if needed

## Environment Variables

### Core (Python)
- `GRPC__ENABLED` - Enable gRPC server (default: false)
- `GRPC__PORT` - gRPC server port (default: 3774)
- `GRPC__HOST` - gRPC server host (default: 0.0.0.0)
- `MONGODB_URI` - MongoDB connection string
- `REDIS_URL` - Redis connection string
- `HYDRA_ADMIN_URL` - Ory Hydra admin API
- `HYDRA_PUBLIC_URL` - Ory Hydra public API

### SDK (TypeScript)
- `BINDU_CORE_HOST` - Core gRPC host (default: localhost)
- `BINDU_CORE_PORT` - Core gRPC port (default: 3774)
- `OPENAI_API_KEY` - For OpenAI examples
- `OPENAI_MODEL` - Model name (default: gpt-4o)

## Links to Key Documentation

- **gRPC Overview**: `docs/grpc/overview.md` - Architecture diagrams, message flow
- **gRPC API Reference**: `docs/grpc/api-reference.md` - Every RPC method, message type
- **TypeScript SDK Guide**: `docs/grpc/sdk-typescript.md` - Installation, usage, patterns
- **Building New SDKs**: `docs/grpc/sdk-development.md` - Step-by-step guide
- **Limitations**: `docs/grpc/limitations.md` - Known gaps (streaming, TLS, etc.)
- **mTLS Deployment**: `docs/MTLS_DEPLOYMENT_GUIDE.md` - Production security setup

## Team Conventions

- **Commit messages**: Follow conventional commits (`feat:`, `fix:`, `docs:`, `test:`)
- **Branch naming**: `feature/description`, `fix/issue-number`, `docs/topic`
- **PR size**: Keep PRs focused - one feature or fix per PR
- **Code review**: At least one approval required
- **Testing**: All PRs must include tests
- **Documentation**: Update docs in the same PR as code changes

## Known Issues & TODOs

- [ ] Streaming responses not implemented for gRPC agents (see `docs/grpc/limitations.md`)
- [ ] No TLS/mTLS yet - only safe on localhost (see `docs/MTLS_DEPLOYMENT_GUIDE.md`)
- [ ] No automatic reconnection if SDK crashes
- [ ] No connection pooling in GrpcAgentClient
- [ ] Frontend needs OAuth2 integration with Hydra
- [ ] Payment webhook verification needs improvement
- [ ] Agent trust validation needs integration tests (PR #399 merged but not tested E2E)

---

**Last Updated**: 2026-03-30
**Maintainer**: Bindu Team
**Questions?** Check docs/ or open an issue on GitHub

# CLAUDE.md - Full Content

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
