---
name: regenerate-grpc-stubs
description: Regenerate Python + TypeScript gRPC stubs after editing proto files. Use when proto/*.proto changes, imports from bindu.grpc.generated fail, CI reports generated-code drift, or HandleMessages calls fail with proto mismatch.
---

# Regenerate gRPC Stubs

## Overview

Bindu's cross-language agents share one proto file: [proto/agent_handler.proto](../../../proto/agent_handler.proto). Two generated stub trees must stay in sync with it:

- `bindu/grpc/generated/` — Python stubs for the core
- `sdks/typescript/src/generated/` — TypeScript stubs for the SDK

Both languages must be regenerated **together** and committed in the same PR as the proto change. A proto change without matching stubs leaves main broken for anyone who pulls.

## Inputs

- `<proto_file>`: usually `proto/agent_handler.proto`, or whatever file was modified under `proto/`.

## Safety

- Do not edit files under `bindu/grpc/generated/` or `sdks/typescript/src/generated/`. Changes will be overwritten by the next regeneration.
- Do not split the proto change and the stub regeneration across PRs. They must land atomically.
- If the proto change is breaking (removed fields, renamed RPCs, changed message types), flag it in the PR description — existing clients will break.

## Execution Contract

1. Confirm the proto change is intentional and minimal.
2. Regenerate both Python and TypeScript stubs via the project's script.
3. Verify both stub trees compile.
4. Run the gRPC integration tests.
5. Commit proto + both generated trees together.

## Steps

### 1. Review the proto diff

```bash
git diff proto/agent_handler.proto
```

For each change, classify:
- **Additive** (new RPC, new field with a new tag) — safe, backward-compatible.
- **Breaking** (removed field, renumbered tag, renamed RPC) — needs a coordination note and a version bump plan.

### 2. Regenerate all stubs

```bash
bash scripts/generate_protos.sh all
```

The script handles both languages and fixes Python import paths. It is the single source of truth — do not run `grpc_tools.protoc` or `grpc_tools_node_protoc` by hand.

### 3. Verify Python stubs

```bash
uv run python -c "from bindu.grpc.generated import agent_handler_pb2, agent_handler_pb2_grpc"
uv run mypy bindu/grpc/
```

### 4. Verify TypeScript stubs

```bash
cd sdks/typescript && npm run build
```

### 5. Run gRPC integration tests

```bash
uv run pytest tests/integration/grpc/ -v
```

### 6. Update docs if the API surface changed

Touch [docs/grpc/api-reference.md](../../../docs/grpc/api-reference.md) for added/removed/modified RPCs. Skip if purely additive internal fields.

### 7. Commit atomically

One commit containing: the proto change, both generated trees, any doc updates. Commit message:

```
refactor(grpc): <describe the proto change>

- proto: <summary>
- regenerated Python + TypeScript stubs
```

## Never do

- **Never edit `bindu/grpc/generated/` or `sdks/typescript/src/generated/` directly.** The diff will be lost the next time anyone regenerates.
- **Never regenerate only one language.** Cross-language drift is the #1 source of confusing gRPC bugs.
- **Never renumber or reuse proto field tags.** That's the one thing protobuf cannot recover from.
