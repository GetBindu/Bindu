# Task State Machine

This document describes the task state machine in Bindu, following the A2A Protocol.

## States

### Non-Terminal States

Tasks in these states are mutable and can receive new messages or be modified.

| State | Description | Can Pause | Can Cancel |
|-------|-------------|-----------|------------|
| `submitted` | Task submitted, awaiting execution | Yes | Yes |
| `working` | Agent actively processing | Yes | Yes |
| `input-required` | Waiting for user input | Yes | Yes |
| `auth-required` | Waiting for authentication | No | Yes |
| `suspended` | Task paused, can be resumed | No | Yes |

### Terminal States

Tasks in these states are immutable - no further changes allowed.

| State | Description |
|-------|-------------|
| `completed` | Successfully completed with artifacts |
| `failed` | Failed due to error |
| `canceled` | Canceled by user |
| `rejected` | Rejected by agent |

## State Transitions

### Valid Transitions

```
submitted ──→ working ──→ completed
    │           │
    │           ├──→ input-required ──→ working
    │           │
    │           ├──→ suspended ──→ working (resume)
    │           │
    │           ├──→ failed
    │           │
    │           └──→ canceled
    │
    ├──→ input-required ──→ working
    │
    ├──→ suspended ──→ working
    │
    ├──→ failed
    │
    ├──→ canceled
    │
    └──→ rejected
```

### Transition Rules

| From State | To State | Valid | Notes |
|------------|----------|-------|-------|
| `submitted` | `working` | ✓ | Task starts processing |
| `submitted` | `input-required` | ✓ | Agent needs clarification |
| `submitted` | `suspended` | ✓ | Task paused before starting |
| `submitted` | `failed` | ✓ | Task rejected before starting |
| `submitted` | `canceled` | ✓ | User canceled before starting |
| `submitted` | `rejected` | ✓ | Agent rejected |
| `working` | `completed` | ✓ | Task finished successfully |
| `working` | `input-required` | ✓ | Agent needs clarification |
| `working` | `suspended` | ✓ | Task paused during execution |
| `working` | `failed` | ✓ | Task failed with error |
| `working` | `canceled` | ✓ | User canceled |
| `input-required` | `working` | ✓ | User provided input |
| `input-required` | `failed` | ✓ | User failed to provide input |
| `input-required` | `canceled` | ✓ | User canceled |
| `suspended` | `working` | ✓ | Task resumed |
| `suspended` | `canceled` | ✓ | User canceled paused task |
| `suspended` | `failed` | ✓ | Task failed while paused |

## Pausable States

Tasks can only be paused from these states:

```python
pausable_states = frozenset({
    "submitted",    # Task submitted, awaiting execution
    "working",      # Agent actively processing
    "input-required"  # Waiting for user input
})
```

## State Machine Configuration

The state machine is configured in `settings.py`:

```python
# Non-terminal states: Task is mutable
non_terminal_states = frozenset({
    "submitted",
    "working", 
    "input-required",
    "auth-required",
    "suspended",
})

# Terminal states: Task is immutable
terminal_states = frozenset({
    "completed",
    "failed",
    "canceled",
    "rejected",
})

# States from which tasks can be paused
pausable_states = frozenset({
    "submitted",
    "working",
    "input-required",
})
```

## Pause/Resume Flow

### Pause

```
1. Validate task is in pausable state
2. Save checkpoint with current task state
3. Update task state to 'suspended'
4. Trigger lifecycle notification
```

### Resume

```
1. Validate task is in 'suspended' state
2. Load checkpoint data
3. Update task state to 'working'
4. Apply checkpoint metadata
5. Trigger lifecycle notification
```

## Implementation

### Storage Layer

The storage layer maintains task state but doesn't enforce transition rules - that's handled at the application/worker layer.

```python
# Update task state
await storage.update_task(task_id, state="working")

# Load task
task = await storage.load_task(task_id)
current_state = task["status"]["state"]
```

### Worker Layer

The worker layer enforces state transition rules and handles pause/resume:

```python
# Check if task can be paused
if current_state not in app_settings.agent.pausable_states:
    return  # Cannot pause

# Pause - save checkpoint and update state
await storage.save_checkpoint(task_id, checkpoint_data)
await storage.update_task(task_id, state="suspended")
```

## Examples

### Complete Workflow

```python
# Submit task
await storage.submit_task(context_id, message)
# State: submitted

# Start working
await storage.update_task(task_id, state="working")
# State: working

# Agent needs clarification
await storage.update_task(task_id, state="input-required")
# State: input-required

# User provides input
await storage.update_task(task_id, state="working")
# State: working

# Task completes
await storage.update_task(task_id, state="completed")
# State: completed (terminal)
```

### Pause/Resume Workflow

```python
# Submit and start
await storage.submit_task(context_id, message)
await storage.update_task(task_id, state="working")
# State: working

# Pause
await storage.save_checkpoint(task_id, {...})
await storage.update_task(task_id, state="suspended")
# State: suspended

# Resume
await storage.update_task(task_id, state="working")
# State: working

# Complete
await storage.update_task(task_id, state="completed")
# State: completed
```

## Testing

Run state transition tests:

```bash
pytest tests/integration/test_state_transitions.py -v
```

Test categories:
- State classification (suspended is non-terminal)
- Valid transitions
- Terminal state immutability
- Non-terminal state mutability
- Complete workflows
