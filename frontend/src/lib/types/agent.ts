export type TaskState =
  | 'submitted'
  | 'working'
  | 'input-required'
  | 'auth-required'
  | 'completed'
  | 'failed'
  | 'canceled'
  | 'rejected';

export interface TaskStatus {
  state: TaskState;
  timestamp: string;
}

export interface MessagePart {
  kind: 'text' | 'artifact' | 'image' | 'file';
  text?: string;
  data?: unknown;
  mimeType?: string;
  filename?: string;
}

export interface Message {
  kind: 'message';
  role: 'user' | 'assistant';
  parts: MessagePart[];
  task_id?: string;
  taskId?: string;
  context_id?: string;
  contextId?: string;
  message_id?: string;
  messageId?: string;
}

export interface Task {
  id: string;
  context_id: string;
  contextId?: string;
  kind: 'task';
  status: TaskStatus;
  history: Message[];
  artifacts: unknown[];
  metadata: Record<string, unknown>;
  referenceTaskIds?: string[];
}

export interface Context {
  id: string;
  context_id?: string;
  task_count?: number;
  taskCount?: number;
  task_ids?: string[];
  taskIds?: string[];
  timestamp?: number;
  firstMessage?: string;
}

export interface JSONRPCRequest {
  jsonrpc: '2.0';
  method: string;
  params: unknown;
  id: string;
}

export interface JSONRPCResponse<T = unknown> {
  jsonrpc: '2.0';
  id: string;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

export interface SendMessageParams extends Record<string, unknown> {
  message: {
    role: 'user';
    parts: MessagePart[];
    kind: 'message';
    messageId: string;
    contextId: string;
    taskId: string;
    referenceTaskIds?: string[];
  };
  configuration: {
    acceptedOutputModes: string[];
  };
}

export interface GetTaskParams {
  taskId: string;
}

export interface ListContextsParams {
  limit?: number;
  offset?: number;
}

export interface ClearContextParams {
  contextId: string;
}

export interface ContextListResult {
  contexts: Context[];
  total: number;
}

export function isTerminalState(state: TaskState): boolean {
  return ['completed', 'failed', 'canceled', 'rejected'].includes(state);
}

export function isNonTerminalState(state: TaskState): boolean {
  return ['input-required', 'auth-required'].includes(state);
}

export function generateUUID(): string {
  return crypto.randomUUID();
}
