# Bindu - Contribution Opportunities

This document outlines all the ways you can contribute to Bindu, based on the project's current needs, roadmap, and areas for improvement.

---

## Quick Summary

| Area | Priority | Difficulty | Good For |
|------|----------|------------|----------|
| Test Coverage | 🔴 High | Easy-Medium | Beginners |
| Rust SDK | 🟡 Medium | Hard | Advanced |
| AP2 Protocol | 🟡 Medium | Medium | Intermediate |
| DSPy Integration | 🟡 Medium | Medium | Intermediate |
| Frontend Features | 🟡 Medium | Easy-Medium | Frontend devs |
| Documentation | 🟢 Low | Easy | Writers |
| Bug Fixes | 🟡 Medium | Varies | All |

---

## 1. Test Coverage (High Priority)

The project targets **70%+ coverage** (goal: 80%). The `coverage.json` shows many files with lower coverage.

### Files with Low Coverage (from coverage.json):
- `bindu/__version__.py` - 38% covered
- `bindu/server/task_manager.py` - needs more tests
- `bindu/penguin/did_setup.py` - needs tests
- `bindu/grpc/` - gRPC client/server tests needed
- `bindu/tunneling/` - tunneling tests needed

### How to Contribute:
```bash
# See what's missing
uv run pytest --cov=bindu --cov-report=term-missing

# Add tests to tests/unit/
# Follow patterns in tests/unit/test_*.py
```

**Good First Issues**: Test the scheduler, storage layer, or add E2E tests.

---

## 2. Roadmap Items (Official Needs)

From README.md roadmap:

### In Progress:
- **DSPy integration** - Basic example exists, needs expansion
- **Increase test coverage to 80%** - Ongoing effort

### Not Started:
- **AP2 end-to-end support** - Agentic commerce protocol
- **Rust SDK** - Language-agnostic support
- **MLTS support** - Multi-language task support
- **X402 with other facilitators** - Beyond Base blockchain

### How to Contribute:
- AP2 integration: Study `docs/PAYMENT.md` and the X402 implementation in `bindu/extensions/x402/`
- Rust SDK: Follow patterns in `sdks/typescript/` and `sdks/kotlin/`

---

## 3. Code TODOs (Immediate Fixes)

Found in the codebase:
- `bindu/server/workers/base.py`:
  - `TODO: Implement task pause functionality`
  - `TODO: Implement task resume functionality`

These are concrete features to implement.

---

## 4. Frontend Contributions (Svelte)

The frontend at `frontend/` is a **SvelteKit** app (not React).

### Areas Needing Work:
- Enhanced agent management UI
- Better real-time updates
- Mobile responsiveness improvements
- Accessibility (partially done)

### Tech Stack:
- SvelteKit
- Tailwind CSS
- TypeScript

### How to Contribute:
```bash
cd frontend
npm install
npm run dev  # Runs on port 5173
```

---

## 5. SDK Development

### TypeScript SDK (`sdks/typescript/`)
- Add more examples
- Improve error handling
- Add streaming support documentation

### Kotlin SDK (`sdks/kotlin/`)
- Basic implementation exists
- Needs more examples and documentation

### What Needs Building:
- **Rust SDK** - High priority, no implementation yet

---

## 6. Documentation

### Needs Updates:
- GRPC documentation (`docs/grpc/`)
- More examples for each agent framework
- API reference generation
- Translation updates (README files exist in 9 languages)

### Documentation Files:
- `docs/AUTHENTICATION.md`
- `docs/PAYMENT.md`
- `docs/STORAGE.md`
- `docs/SCHEDULER.md`
- `docs/SKILLS.md`
- `docs/NEGOTIATION.md`
- `docs/TUNNELING.md`
- `docs/NOTIFICATIONS.md`
- `docs/OBSERVABILITY.md`
- `docs/DID.md`
- `docs/HEALTH_METRICS.md`
- `docs/GRPC_LANGUAGE_AGNOSTIC.md`
- `docs/MTLS_DEPLOYMENT_GUIDE.md`
- `docs/VAULT_INTEGRATION.md`

---

## 7. Agent Framework Integrations

The project supports:
- Python: AG2, Agno, CrewAI, LangChain, LangGraph, LlamaIndex, FastAgent
- TypeScript: OpenAI SDK, LangChain.js
- Kotlin: OpenAI Kotlin SDK
- Any language via gRPC

### How to Add a New Framework:
1. Create example in `examples/<framework>-example/`
2. Document in README
3. Add to supported frameworks list

---

## 8. Examples to Build

Looking at `examples/`, there's a gap:
- ✅ beginner/ - Good collection
- ✅ agent_swarm/ - Multi-agent
- ✅ medical_agent/
- ✅ pdf_research_agent/
- ❌ **More swarm examples**
- ❌ **Real-world production examples**
- ❌ **Edge AI / embedded examples**

---

## 9. Bug Fixes & Features

Check GitHub issues for:
- Open bugs
- Feature requests
- Good first issue标签

---

## How to Start Contributing

### 1. Set Up Development Environment
```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

### 2. Run Tests to Verify Setup
```bash
uv run pytest tests/unit/ -v
```

### 3. Pick an Area
- **Beginner**: Add tests to under-covered files
- **Intermediate**: Fix TODOs, add features
- **Advanced**: Build Rust SDK, implement AP2

### 4. Join the Community
- **Discord**: https://discord.gg/3w5zuYUuwt
- **Discussions**: GitHub Discussions
- **Weekly meetups** - Check Discord for schedule

---

## Project Standards

- **Python**: 3.12+, async/await patterns
- **Testing**: pytest, 70%+ coverage target
- **Code Style**: Ruff, pre-commit hooks required
- **Commits**: Conventional commits preferred
- **PRs**: All tests must pass, coverage should not decrease

---

## Key Contacts

- **Lead Maintainer**: Raahul Dutta (@raahul) - `raahul@getbindu.com`
- **Discord**: https://discord.gg/3w5zuYUuwt
- **Website**: https://getbindu.com
- **Docs**: https://docs.getbindu.com

---

*Last updated: 2026-04-10*