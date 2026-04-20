-- Compaction + revert support for the session module.
-- Adds per-message flags and a session-level compaction summary pointer.

alter table gateway_messages add column if not exists compacted boolean not null default false;
alter table gateway_messages add column if not exists reverted  boolean not null default false;

create index if not exists gateway_messages_active_idx
  on gateway_messages (session_id, created_at)
  where compacted = false and reverted = false;

-- Session-level:
--   compaction_summary = most recent summary text inserted into history
--   compaction_at      = when the latest summary was generated
alter table gateway_sessions add column if not exists compaction_summary text;
alter table gateway_sessions add column if not exists compaction_at      timestamptz;

-- Tasks also get a reverted flag so we can hide audit rows from resume
alter table gateway_tasks    add column if not exists reverted  boolean not null default false;
create index if not exists gateway_tasks_active_idx
  on gateway_tasks (session_id, started_at)
  where reverted = false;
