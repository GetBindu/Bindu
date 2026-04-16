# Task Pause/Resume Implementation Guide

## Overview

This document explains how the Task Pause/Resume feature was implemented in Bindu. This feature allows long-running tasks to be paused and resumed, giving users control over task lifecycle.

---

## What Was Implemented

### States
- **Pause**: `working` → `suspended`
- **Resume**: `suspended` → `resumed` → `working` (re-queued for execution)

### API Methods
```json
// Pause a task
{
  "method": "tasks/pause",
  "params": { "taskId": "uuid" }
}

// Resume a task
{
  "method": "tasks/resume",
  "params": { "taskId": "uuid" }
}
```

---

## Files Modified

| File | Changes |
|------|---------|
| `bindu/common/protocol/types.py` | Added error types and request/response types |
| `bindu/settings.py` | Added method handlers and non-terminal states |
| `bindu/server/task_manager.py` | Added router methods |
| `bindu/server/handlers/task_handlers.py` | Implemented handlers with validation |
| `bindu/server/workers/base.py` | Implemented `_handle_pause()` and `_handle_resume()` |

---

## Implementation Details

### 1. Error Types (types.py)

Two new error types for clear API responses:

```python
TaskNotPausableError = JSONRPCError[
    Literal[-32007],
    Literal["This task cannot be paused in its current state. Tasks can only be paused while in 'working' state."]
]

TaskNotResumableError = JSONRPCError[
    Literal[-32008],
    Literal["This task cannot be resumed in its current state. Tasks can only be resumed while in 'suspended' state."]
]
```

### 2. Request/Response Types (types.py)

```python
PauseTaskRequest = JSONRPCRequest[Literal["tasks/pause"], TaskIdParams]
PauseTaskResponse = JSONRPCResponse[Task, Union[TaskNotPausableError, TaskNotFoundError]]

ResumeTaskRequest = JSONRPCRequest[Literal["tasks/resume"], TaskIdParams]
ResumeTaskResponse = JSONRPCResponse[Task, Union[TaskNotResumableError, TaskNotFoundError]]
```

### 3. A2ARequest Union

**Critical**: Added the new types to the A2ARequest discriminated union:

```python
A2ARequest = Annotated[
    Union[
        # ... existing types ...
        PauseTaskRequest,
        ResumeTaskRequest,
        # ...
    ],
    Discriminator("method"),
]
```

### 4. Method Handlers (settings.py)

```python
method_handlers: dict[str, str] = {
    # ... existing ...
    "tasks/pause": "pause_task",
    "tasks/resume": "resume_task",
}

non_terminal_states: frozenset[str] = frozenset({
    "submitted", "working", "input-required", "auth-required",
    "suspended",  # ADDED
    "resumed",    # ADDED
})
```

### 5. TaskHandlers (task_handlers.py)

```python
async def pause_task(self, request):
    task_id = request["params"]["task_id"]
    task = await self.storage.load_task(task_id)

    # Validate state - can only pause working tasks
    if task["status"]["state"] != "working":
        return error(TaskNotPausableError)

    # Send to scheduler → worker
    await self.scheduler.pause_task(request["params"])
    return result(task)

async def resume_task(self, request):
    task_id = request["params"]["task_id"]
    task = await self.storage.load_task(task_id)

    # Validate state - can only resume suspended tasks
    if task["status"]["state"] != "suspended":
        return error(TaskNotResumableError)

    # Send to scheduler → worker
    await self.scheduler.resume_task(request["params"])
    return result(task)
```

### 6. Worker Handlers (workers/base.py)

```python
async def _handle_pause(self, params):
    task_id = self._normalize_uuid(params["task_id"])
    task = await self.storage.load_task(task_id)

    if task:
        # Update state to suspended
        await self.storage.update_task(task_id, state="suspended")

async def _handle_resume(self, params):
    task_id = self._normalize_uuid(params["task_id"])
    task = await self.storage.load_task(task_id)

    if task:
        # Update state to resumed
        await self.storage.update_task(task_id, state="resumed")

        # Re-queue task for execution
        await self.scheduler.run_task(TaskSendParams(
            task_id=task_id,
            context_id=task["context_id"],
            message=task["history"][0]
        ))
```

---

## Flow Diagram

```
Client
   │
   ├─► tasks/pause ──► TaskManager.pause_task()
   │                      │
   │                      ├─► Validate state == "working"
   │                      │
   │                      ├─► scheduler.pause_task() ──► Queue operation
   │                      │
   │                      └─► Reload task
   │
   │   [Worker picks up pause operation]
   │                      │
   │                      └─► Worker._handle_pause() ──► storage.update_task(state="suspended")
   │
   └─► tasks/resume ──► TaskManager.resume_task()
                          │
                          ├─► Validate state == "suspended"
                          │
                          ├─► scheduler.resume_task() ──► Queue operation
                          │
                          └─► Reload task
                                │
                                └─► Worker._handle_resume() ──►
                                                              ├─► update_task(state="resumed")
                                                              └─► run_task() ──► Re-executes
```

---

## Validation Rules

| Operation | Valid State | Invalid States |
|-----------|-------------|----------------|
| pause | `working` | submitted, completed, failed, canceled, suspended, resumed, input-required, auth-required |
| resume | `suspended` | working, submitted, completed, failed, canceled, resumed, input-required, auth-required |

---

## Testing

A test script was created that validates:

1. **Pause working task** → Success, state becomes "suspended"
2. **Pause completed task** → Fails with TaskNotPausableError
3. **Resume suspended task** → Success, task re-queued
4. **Resume working task** → Fails with TaskNotResumableError

### Important: Async Handler Required

For pause/resume to work, the agent handler MUST be async and use `asyncio.sleep()`:

```python
# ✅ CORRECT - Non-blocking
async def handler(messages):
    await asyncio.sleep(5)  # Task stays in "working" state, can be paused
    return [{"role": "assistant", "content": "..."}]

# ❌ WRONG - Blocks event loop
def handler(messages):
    time.sleep(5)  # Blocks everything, pause cannot be processed!
    return [{"role": "assistant", "content": "..."}]
```

**Why?** `time.sleep()` blocks the entire Python event loop, preventing pause/resume operations from being processed. `asyncio.sleep()` yields control, allowing other operations.

---

## What Was Tried Before (Brief)

1. **Fast echo agent** - Tasks complete in <1ms, impossible to catch in "working" state
2. **time.sleep(5)** - Blocked the event loop, pause couldn't be processed at all
3. **blocking: false config** - This configuration is read but never used in the codebase

---

## Usage Example

```python
# Agent handler (must be async for pause/resume to work)
async def handler(messages):
    await asyncio.sleep(10)  # Long-running task
    return [{"role": "assistant", "content": "result"}]
```

```bash
# Send task (non-blocking)
curl -X POST http://localhost:3773/ \
  -d '{"method":"message/send","params":{"message":{"..."},"configuration":{"blocking":false}}}'

# Pause the task (while in working state)
curl -X POST http://localhost:3773/ \
  -d '{"method":"tasks/pause","params":{"taskId":"uuid"}}'

# Resume the task
curl -X POST http://localhost:3773/ \
  -d '{"method":"tasks/resume","params":{"taskId":"uuid"}}'
```

---

## Summary

The pause/resume feature was implemented by:
1. Adding error types and request/response types
2. Registering them in the A2ARequest union
3. Adding method handlers in settings
4. Implementing TaskHandlers with state validation
5. Implementing Worker handlers to actually update state

The key insight is that **async handlers must use `asyncio.sleep()` not `time.sleep()`** to allow pause/resume operations to be processed while the task is running.
