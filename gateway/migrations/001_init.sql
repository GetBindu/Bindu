-- Bindu Gateway — initial session schema (Phase 1).
-- Three tables. RLS enabled as defense-in-depth; service role bypasses it.
-- Phase 2 migrations add tenant_id + TTL pruning.

create extension if not exists "pgcrypto";

create table if not exists gateway_sessions (
  id                   uuid primary key default gen_random_uuid(),
  external_session_id  text unique,                          -- caller-supplied resume key
  user_prefs           jsonb not null default '{}'::jsonb,
  agent_catalog        jsonb not null default '[]'::jsonb,   -- last-seen agents for this session
  created_at           timestamptz not null default now(),
  last_active_at       timestamptz not null default now()
);
create index if not exists gateway_sessions_ext_idx on gateway_sessions (external_session_id);
create index if not exists gateway_sessions_active_idx on gateway_sessions (last_active_at);

create table if not exists gateway_messages (
  id          uuid primary key default gen_random_uuid(),
  session_id  uuid not null references gateway_sessions(id) on delete cascade,
  role        text not null check (role in ('user','assistant','system')),
  parts       jsonb not null,                                -- MessageV2 Part[] shape
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists gateway_messages_session_idx on gateway_messages (session_id, created_at);

create table if not exists gateway_tasks (
  id            uuid primary key default gen_random_uuid(),
  session_id    uuid not null references gateway_sessions(id) on delete cascade,
  agent_name    text not null,
  skill_id      text,
  endpoint_url  text not null,
  remote_task_id text,                                        -- task_id the peer assigned
  remote_context_id text,
  input         jsonb,
  output_text   text,
  state         text not null default 'submitted',            -- submitted|working|completed|failed|canceled|rejected|input-required|auth-required
  usage         jsonb,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz
);
create index if not exists gateway_tasks_session_idx on gateway_tasks (session_id, started_at);
create index if not exists gateway_tasks_remote_idx on gateway_tasks (remote_task_id);

alter table gateway_sessions enable row level security;
alter table gateway_messages enable row level security;
alter table gateway_tasks    enable row level security;

-- Phase 1: service-role-only access. No PUBLIC policies. Service role bypasses RLS.
-- Phase 2: add tenant_id column + tenant_isolation policy.
