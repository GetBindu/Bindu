# Checkpoint System

The checkpoint system enables pause/resume functionality for long-running tasks, allowing them to be suspended and resumed later from the same point without losing progress.

## Overview

Checkpoints store the execution state of a task at a specific point in time. When a task is paused, its current state is saved to persistent storage. When the task is resumed, the checkpoint is retrieved and the task continues from where it left off.

## Checkpoint Data Structure

```python
{
    "task_id": "uuid",
    "checkpoint_data": {
        "task_state": "working",
        "history": [...],
        "artifacts": [...],
        "metadata": {...}
    },
    "step_number": 0,
    "step_label": "processing",
    "created_at": "2024-01-01T00:00:00Z"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | UUID | Unique identifier of the task |
| `checkpoint_data` | JSON | Execution state including task state, history, artifacts, and metadata |
| `step_number` | int | Current step in execution (0-based) |
| `step_label` | str | Optional label for the current step |
| `created_at` | datetime | When the checkpoint was created |

## Checkpoint Lifecycle

### 1. Creation (Pause)

When a task is paused:

1. **Validation**: Check if task is in a pausable state (`submitted`, `working`, `input-required`)
2. **Save**: Create checkpoint with current task state
3. **Update State**: Change task state to `suspended`
4. **Notify**: Trigger lifecycle notification

```
working → pause → suspended
```

### 2. Retrieval (Resume)

When a task is resumed:

1. **Validation**: Check if task is in `suspended` state
2. **Load**: Retrieve latest checkpoint
3. **Update State**: Change task state to `working`
4. **Restore**: Apply checkpoint metadata to task

```
suspended → resume → working
```

### 3. Cleanup

Checkpoints are automatically deleted when:

- Task reaches terminal state: `completed`, `failed`, `canceled`, `rejected`
- Task is explicitly deleted

## Storage

### PostgreSQL

Checkpoints are stored in the `task_checkpoints` table:

```sql
CREATE TABLE task_checkpoints (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    checkpoint_data JSONB NOT NULL,
    step_number INTEGER NOT NULL DEFAULT 0,
    step_label VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_checkpoints_task_id ON task_checkpoints(task_id);
CREATE INDEX idx_task_checkpoints_created_at ON task_checkpoints(created_at DESC);
```

### Memory Storage

For development/testing, in-memory storage maintains checkpoints in a dictionary.

## API

### Storage Interface

```python
# Save a checkpoint
await storage.save_checkpoint(
    task_id: UUID,
    checkpoint_data: dict,
    step_number: int = 0,
    step_label: str | None = None
)

# Get latest checkpoint
checkpoint = await storage.get_checkpoint(task_id: UUID)
# Returns: {checkpoint_data, step_number, step_label, created_at} or None

# Delete checkpoint(s)
await storage.delete_checkpoint(task_id: UUID)

# List checkpoints (optionally filtered by task_id)
checkpoints = await storage.list_checkpoints(task_id: UUID | None = None, limit: int = 100)

# Cleanup old checkpoints
deleted_count = await storage.cleanup_old_checkpoints(days_old: int = 7)
```

### Worker Interface

```python
# Pause a task
await worker._handle_pause(TaskIdParams(task_id=...))

# Resume a task  
await worker._handle_resume(TaskIdParams(task_id=...))
```

## Configuration

### Pausable States

Tasks can only be paused from these states:

```python
pausable_states = frozenset({
    "submitted",    # Task submitted, awaiting execution
    "working",      # Agent actively processing
    "input-required"  # Waiting for user input
})
```

## Best Practices

1. **Frequent Checkpoints**: For long-running tasks, save checkpoints periodically during execution
2. **Minimal Data**: Store only essential state in checkpoints to minimize storage
3. **Cleanup**: Ensure checkpoints are cleaned up after task completion
4. **Idempotency**: Pause/resume operations should be idempotent

## Example Usage

```python
# Pause a task
await worker._handle_pause({"task_id": task_id})
# Task is now suspended, checkpoint saved

# Resume a task
await worker._handle_resume({"task_id": task_id})
# Task is now working, continues from checkpoint
```

## Error Handling

- **Pause non-pausable task**: Silently returns without action (logs warning)
- **Resume without checkpoint**: Silently returns without action (logs warning)
- **Resume non-suspended task**: Silently returns without action (logs warning)
