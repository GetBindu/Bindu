# AGENTS.md

Canonical guide for AI coding agents (Claude Code, Codex, Cursor, Copilot, Windsurf, etc.) contributing to Bindu.

Keep this file agent-agnostic. Claude-specific detail lives in [CLAUDE.md](CLAUDE.md); automatable playbooks live in [.agents/skills/](.agents/skills/).

## Repo orientation

Bindu is a framework for running AI agents as DID-identified, A2A-speaking microservices. Core is Python (FastAPI + gRPC). Thin SDKs (`sdks/typescript/`, planned Kotlin) wrap a shared gRPC service. See [CLAUDE.md §Architecture](CLAUDE.md) for the full picture.

## Useful commands

```bash
# Python core
uv sync                          # Install deps (run after pulling)
uv run pytest tests/unit/        # Fast feedback
uv run pytest                    # Full suite
uv run ruff check . && uv run ruff format .
uv run mypy bindu
uv run pre-commit run --all-files  # Run this before every commit

# Run the core
bindu serve --grpc               # HTTP + gRPC server
lsof -ti:3773 -ti:3774           # Check which ports are bound

# TypeScript SDK
cd sdks/typescript && npm run build

# Frontend dashboard (port 5173)
cd frontend && npm run dev

# gRPC stub regeneration (after editing proto/agent_handler.proto)
bash scripts/generate_protos.sh all
```

## Agent file routing

| File | Purpose |
| --- | --- |
| `AGENTS.md` (this file) | Agent-agnostic entry point. Start here. |
| [CLAUDE.md](CLAUDE.md) | Full project context with Claude-specific guidance. Richer than this file — read it when you have room. |
| [.agents/skills/](.agents/skills/) | Task-specific playbooks with YAML frontmatter. Load the frontmatter to decide when to apply; load the body only when triggered. |
| [.agents/README.md](.agents/README.md) | Skill index and workflow conventions. |

## Contribution policy

These rules are mandatory for AI-assisted contributions. They match the spirit of HuggingFace's AGENTS.md policy — a human must own every PR.

### Coordinate before coding

- If the work maps to an open issue, discuss on that issue before opening a PR.
- Don't open a PR against someone else's issue without their approval in the thread.
- Check for duplicate work before starting:
  ```bash
  gh issue view <n> --repo GetBindu/Bindu --comments
  gh pr list --repo GetBindu/Bindu --state open --search "<keywords>"
  ```

### No low-value PRs

- No one-off typo fixes, isolated lint-only changes, or mechanical cleanups as standalone PRs.
- Bundle trivial fixes into meaningful changes, or skip them.
- Every PR must have a clear "why" — the problem being solved, not just what changed.

### Accountability for AI-assisted patches

- A human submitter must understand and defend every changed line.
- AI-assisted PR descriptions must include:
  - Link to the coordinating issue (or explanation if there isn't one).
  - Test commands run and their results.
  - Clear statement that AI assistance was used.
- Do not open PRs without human validation of the full diff.

### Fail-closed behavior

If coordination context is missing, if the work duplicates an open PR, or if the scope is trivial busywork — **stop and explain what's missing**. Do not produce a PR regardless.

## Codebase gotchas (short list)

The full list is in [CLAUDE.md §Gotchas](CLAUDE.md). The ones agents get wrong most often:

- **Never edit generated code** under `bindu/grpc/generated/` or `sdks/typescript/src/generated/`. Edit [proto/agent_handler.proto](proto/agent_handler.proto) and regenerate — see [.agents/skills/regenerate-grpc-stubs/](.agents/skills/regenerate-grpc-stubs/).
- **Use `get_logger(__name__)`** from `bindu/utils/logging.py`, not `print()`.
- **Use `app_settings`** from [bindu/settings.py](bindu/settings.py) for config, not env-var reads.
- **Use `dict.pop(key, None)`**, not `del dict[key]`, for optional keys.
- **Never commit `.env` files**; `.env.example` only, with `# pragma: allowlist secret` to bypass pre-commit secret scans.
- **Keep PRs focused** — one feature or fix per PR. Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`).
