# CLAUDE.md

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

---

# Bindu - Claude Code Context

## Current Focus: Task Pause/Resume Feature Implementation

This document tracks the implementation plan for the Task Pause/Resume feature (GitHub Issue #383).

---

## Background

The pause/resume functionality is **not implemented** in either the fork or upstream. Despite PR #357 claiming implementation, the code in `workers/base.py` still has:
```python
async def _handle_pause(self, params):
    raise NotImplementedError("Pause operation not yet implemented")
```

---

## Test Cases to Pass

### Pause Operation
| # | Test Case | Expected |
|---|-----------|----------|
| 1 | Pause task in `working` state | ✅ Success → `suspended` |
| 2 | Pause task in `submitted` state | ❌ TaskNotPausableError |
| 3 | Pause task in `completed` state | ❌ TaskNotPausableError |
| 4 | Pause task in `failed` state | ❌ TaskNotPausableError |
| 5 | Pause task in `canceled` state | ❌ TaskNotPausableError |
| 6 | Pause task in `suspended` state | ❌ TaskNotPausableError |
| 7 | Pause task in `input-required` state | ❌ TaskNotPausableError |
| 8 | Pause task in `auth-required` state | ❌ TaskNotPausableError |
| 9 | Pause non-existent task | ❌ TaskNotFoundError |

### Resume Operation
| # | Test Case | Expected |
|---|-----------|----------|
| 1 | Resume task in `suspended` state | ✅ Success → `resumed` |
| 2 | Resume task in `working` state | ❌ TaskNotResumableError |
| 3 | Resume task in `completed` state | ❌ TaskNotResumableError |
| 4 | Resume task in `failed` state | ❌ TaskNotResumableError |
| 5 | Resume task in `canceled` state | ❌ TaskNotResumableError |
| 6 | Resume task in `submitted` state | ❌ TaskNotResumableError |
| 7 | Resume task in `input-required` state | ❌ TaskNotResumableError |
| 8 | Resume task in `resumed` state | ❌ TaskNotResumableError |
| 9 | Resume non-existent task | ❌ TaskNotFoundError |

---

## Implementation Phases

### Phase 1: Foundation (Prerequisites)
- [x] 1.1 Add error types (`TaskNotPausableError`, `TaskNotResumableError`) to `types.py`
- [x] 1.2 Add request/response types (`PauseTaskRequest/Response`, `ResumeTaskRequest/Response`) to `types.py`
- [x] 1.3 Add method handlers in `settings.py` (`tasks/pause`, `tasks/resume`)
- [x] 1.4 Add router methods in `task_manager.py`

### Phase 2: Implement PAUSE
- [x] 2.1 Implement `TaskHandlers.pause_task()` with state validation
- [x] 2.2 Implement `Worker._handle_pause()`
- [x] 2.3 Add `"suspended"` to `non_terminal_states` in settings
- [ ] 2.4 Manual test pause flow

### Phase 3: Implement RESUME
- [x] 3.1 Implement `TaskHandlers.resume_task()` with state validation
- [x] 3.2 Implement `Worker._handle_resume()`
- [x] 3.3 Add `"resumed"` to `non_terminal_states` in settings
- [ ] 3.4 Manual test resume flow

### Phase 4: Polish
- [ ] 4.1 Add unit tests
- [ ] 4.2 Full integration test

---

## Validation Rules

| Operation | Valid State | Invalid States |
|-----------|-------------|----------------|
| pause | `working` | All others (submitted, completed, failed, canceled, suspended, resumed, input-required, auth-required) |
| resume | `suspended` | All others (working, submitted, completed, failed, canceled, resumed, input-required, auth-required) |

---

## Files to Modify

1. `bindu/common/protocol/types.py` - Error types + request/response types
2. `bindu/settings.py` - Method handlers + non-terminal states
3. `bindu/server/task_manager.py` - Router methods
4. `bindu/server/handlers/task_handlers.py` - Handler logic with validation
5. `bindu/server/workers/base.py` - `_handle_pause()` and `_handle_resume()`

---

## Key Design Decisions

1. **No over-engineering**: Check state in TaskHandlers only, Worker does minimal state update
2. **Checkpoint is metadata only**: Save timestamp and history count, not full history (already in storage)
3. **Resumed → working flow**: Resume updates to "resumed", scheduler re-runs which sets to "working"
4. **Error types**: Use TaskNotPausableError/TaskNotResumableError matching existing patterns

---

## Related Issues
- #383: Bug - Unimplemented Task Pause/Resume Functionality in Base Worker
- #356: Feature - Task Pause/Resume (design doc)
- #357: Implementation PR (incomplete)

---

## Important Notes

- Upstream repo: https://github.com/GetBindu/Bindu
- This fork: https://github.com/pkonal23/Bindu
- Issue #383 is from upstream - same problem exists in both
