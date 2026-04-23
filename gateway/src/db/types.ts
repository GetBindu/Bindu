/**
 * Canonical row shapes for the Bindu Gateway's Supabase-backed tables.
 *
 * These mirror migrations/001_init.sql exactly. Consumers should use these
 * types instead of hand-rolling shapes.
 */

export interface SessionRow {
  id: string
  external_session_id: string | null
  user_prefs: Record<string, unknown>
  agent_catalog: unknown[]
  created_at: string
  last_active_at: string
}

export interface MessageRow {
  id: string
  session_id: string
  role: "user" | "assistant" | "system"
  parts: unknown[]
  metadata: Record<string, unknown>
  created_at: string
}

export interface TaskRow {
  id: string
  session_id: string
  agent_name: string
  skill_id: string | null
  endpoint_url: string
  remote_task_id: string | null
  remote_context_id: string | null
  input: unknown | null
  output_text: string | null
  state: string
  usage: Record<string, unknown> | null
  started_at: string
  finished_at: string | null
}

export type TaskState =
  | "submitted"
  | "working"
  | "input-required"
  | "auth-required"
  | "completed"
  | "failed"
  | "canceled"
  | "rejected"

export const TERMINAL_STATES: readonly TaskState[] = [
  "completed",
  "failed",
  "canceled",
  "rejected",
] as const

export function isTerminal(state: string): boolean {
  return (TERMINAL_STATES as readonly string[]).includes(state)
}
