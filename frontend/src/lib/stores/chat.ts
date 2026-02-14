import { writable, get } from 'svelte/store';
import type { Task, Context, TaskState } from '$lib/types/agent';
import { isTerminalState, isNonTerminalState, generateUUID } from '$lib/types/agent';
import { agentAPI } from '$lib/services/agent-api';

export interface DisplayMessage {
  id: string;
  text: string;
  role: 'user' | 'assistant' | 'status';
  taskId?: string;
  state?: TaskState;
  timestamp: number;
}

export const currentTaskId = writable<string | null>(null);
export const currentTaskState = writable<TaskState | null>(null);
export const contextId = writable<string | null>(null);
export const replyToTaskId = writable<string | null>(null);
export const messages = writable<DisplayMessage[]>([]);
export const contexts = writable<Context[]>([]);
export const authToken = writable<string | null>(null);
export const isThinking = writable<boolean>(false);
export const error = writable<string | null>(null);

let pollingInterval: ReturnType<typeof setInterval> | null = null;

export function initializeAuth() {
  if (typeof window !== 'undefined') {
    // Use the OAuth token from the settings page (optional)
    const token = localStorage.getItem('bindu_oauth_token');
    console.log('=== Initializing Auth ===');
    console.log('Token from localStorage (bindu_oauth_token):', token ? `${token.substring(0, 20)}...` : 'NULL (auth is optional)');

    if (token) {
      console.log('Setting token in store and API client');
      authToken.set(token);
      agentAPI.setAuthToken(token);
      console.log('Token set successfully');
    } else {
      console.log('No token found - continuing without authentication (auth is optional)');
      // Set null token to allow API calls without auth
      agentAPI.setAuthToken(null);
    }
  }
}

export function setAuth(token: string | null) {
  console.log('Setting auth token:', token ? `${token.substring(0, 20)}...` : 'null');
  authToken.set(token);
  agentAPI.setAuthToken(token);
  // Also save to the same localStorage key used by settings page
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('bindu_oauth_token', token);
    } else {
      localStorage.removeItem('bindu_oauth_token');
    }
  }
}

export function addMessage(text: string, role: 'user' | 'assistant' | 'status', taskId?: string, state?: TaskState) {
  const message: DisplayMessage = {
    id: generateUUID(),
    text,
    role,
    taskId,
    state,
    timestamp: Date.now()
  };
  messages.update(msgs => [...msgs, message]);
}

export function clearMessages() {
  messages.set([]);
}

export function setError(errorMessage: string | null) {
  error.set(errorMessage);
}

export async function loadContexts() {
  try {
    const serverContexts = await agentAPI.listContexts();

    const transformedContexts = serverContexts.map(ctx => ({
      id: ctx.context_id || ctx.id,
      context_id: ctx.context_id || ctx.id,
      task_count: ctx.task_count || ctx.taskCount || 0,
      taskCount: ctx.task_count || ctx.taskCount || 0,
      task_ids: ctx.task_ids || ctx.taskIds || [],
      taskIds: ctx.task_ids || ctx.taskIds || [],
      timestamp: Date.now(),
      firstMessage: 'Loading...'
    }));

    for (const ctx of transformedContexts) {
      if (ctx.taskIds && ctx.taskIds.length > 0) {
        try {
          const task = await agentAPI.getTask(ctx.taskIds[0]);
          const history = task.history || [];

          for (const msg of history) {
            if (msg.role === 'user') {
              const parts = msg.parts || [];
              const textParts = parts
                .filter(part => part.kind === 'text')
                .map(part => part.text || '');
              if (textParts.length > 0) {
                ctx.firstMessage = textParts[0].substring(0, 50);
                break;
              }
            }
          }

          if (task.status && task.status.timestamp) {
            ctx.timestamp = new Date(task.status.timestamp).getTime();
          }
        } catch (err) {
          console.error('Error loading context preview:', err);
        }
      }
    }

    contexts.set(transformedContexts);
  } catch (err) {
    console.error('Error loading contexts:', err);
    setError('Failed to load contexts');
  }
}

export async function switchContext(ctxId: string) {
  try {
    console.log('=== SWITCH CONTEXT START ===', ctxId);
    clearMessages();
    contextId.set(ctxId);
    console.log('Context ID set to:', ctxId);

    const allContexts = get(contexts);
    const selectedContext = allContexts.find(c => c.id === ctxId);
    console.log('Selected context:', selectedContext);

    if (!selectedContext || !selectedContext.taskIds || selectedContext.taskIds.length === 0) {
      console.log('No context or no tasks found');
      return;
    }

    console.log('Loading tasks:', selectedContext.taskIds);
    const contextTasks: Task[] = [];
    for (const taskId of selectedContext.taskIds) {
      try {
        console.log('Fetching task:', taskId);
        const task = await agentAPI.getTask(taskId);
        console.log('Task loaded:', task.id, 'History length:', task.history?.length);
        contextTasks.push(task);
      } catch (err) {
        console.error(`Error loading task ${taskId}:`, err);
      }
    }

    console.log('Sorting', contextTasks.length, 'tasks');
    contextTasks.sort((a, b) => {
      const timeA = new Date(a.status.timestamp).getTime();
      const timeB = new Date(b.status.timestamp).getTime();
      return timeA - timeB;
    });

    console.log('Processing task history into messages...');
    let messageCount = 0;
    for (const task of contextTasks) {
      const history = task.history || [];
      for (const msg of history) {
        const parts = msg.parts || [];
        const textParts = parts
          .filter(part => part.kind === 'text')
          .map(part => part.text || '');

        if (textParts.length > 0) {
          const text = textParts.join('\n');
          const sender = msg.role === 'user' ? 'user' : 'assistant';
          const state = sender === 'assistant' ? task.status.state : undefined;
          addMessage(text, sender, task.id, state);
          messageCount++;
        }
      }
    }

    console.log('Added', messageCount, 'messages to display');
    console.log('Current messages store length:', get(messages).length);

    if (contextTasks.length > 0) {
      const lastTask = contextTasks[contextTasks.length - 1];
      currentTaskId.set(lastTask.id);
      currentTaskState.set(lastTask.status.state);
      console.log('Set current task:', lastTask.id, 'State:', lastTask.status.state);
    }

    console.log('=== SWITCH CONTEXT END ===');
  } catch (err) {
    console.error('Error switching context:', err);
    setError('Failed to load context');
  }
}

export function createNewContext() {
  contextId.set(null);
  currentTaskId.set(null);
  currentTaskState.set(null);
  replyToTaskId.set(null);
  clearMessages();
}

export async function clearContext(ctxId: string) {
  try {
    await agentAPI.clearContext(ctxId);

    contexts.update(ctxs => ctxs.filter(c => c.id !== ctxId));

    if (get(contextId) === ctxId) {
      createNewContext();
    }

    addMessage('Context cleared successfully', 'status');
  } catch (err) {
    console.error('Error clearing context:', err);
    setError('Failed to clear context');
  }
}

export async function sendMessage(text: string) {
  const currentState = get(currentTaskState);
  const currentTask = get(currentTaskId);
  const currentContext = get(contextId);
  const replyTo = get(replyToTaskId);

  // Determine task ID based on A2A protocol
  let taskId: string;
  const referenceTaskIds: string[] = [];

  if (replyTo) {
    // Explicit reply: new task with reference
    taskId = generateUUID();
    referenceTaskIds.push(replyTo);
  } else if (currentState && isNonTerminalState(currentState) && currentTask) {
    // Non-terminal state: reuse task
    taskId = currentTask;
  } else if (currentTask) {
    // Terminal state: new task with reference
    taskId = generateUUID();
    referenceTaskIds.push(currentTask);
  } else {
    // No current task: new task
    taskId = generateUUID();
  }

  const messageId = generateUUID();
  const useContextId = currentContext || generateUUID();

  try {
    // Add user message immediately
    addMessage(text, 'user', taskId);
    replyToTaskId.set(null);
    isThinking.set(true);

    // Send to agent
    const task = await agentAPI.sendMessage({
      message: {
        role: 'user' as const,
        parts: [{ kind: 'text' as const, text }],
        kind: 'message' as const,
        messageId,
        contextId: useContextId,
        taskId,
        ...(referenceTaskIds.length > 0 && { referenceTaskIds })
      },
      configuration: {
        acceptedOutputModes: ['application/json']
      }
    });

    // Set context ID only once on first message
    if (!currentContext) {
      const taskContextId = task.context_id || task.contextId || useContextId;
      contextId.set(taskContextId);
    }

    // Update current task
    currentTaskId.set(task.id);

    // Start polling for response
    startPollingTask(task.id);
  } catch (err) {
    console.error('Error sending message:', err);
    setError(err instanceof Error ? err.message : 'Failed to send message');
    isThinking.set(false);
  }
}

function startPollingTask(taskId: string) {
  // Clear any existing polling
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }

  let lastHistoryLength = 0;

  pollingInterval = setInterval(async () => {
    try {
      const task = await agentAPI.getTask(taskId);
      const history = task.history || [];

      // Add new assistant messages
      if (history.length > lastHistoryLength) {
        for (let i = lastHistoryLength; i < history.length; i++) {
          const msg = history[i];
          if (msg.role === 'assistant') {
            const textParts = (msg.parts || [])
              .filter(part => part.kind === 'text')
              .map(part => part.text || '');

            if (textParts.length > 0) {
              addMessage(textParts.join('\n'), 'assistant', task.id, task.status.state);
            }
          }
        }
        lastHistoryLength = history.length;
      }

      // Update task state
      currentTaskState.set(task.status.state);

      // Stop polling on terminal state
      if (isTerminalState(task.status.state)) {
        isThinking.set(false);
        if (pollingInterval) {
          clearInterval(pollingInterval);
          pollingInterval = null;
        }
      }
    } catch (err) {
      console.error('Error polling task:', err);
      isThinking.set(false);
      if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
    }
  }, 1000);
}

export function setReplyTo(taskId: string | null) {
  replyToTaskId.set(taskId);
}

export function clearReplyTo() {
  replyToTaskId.set(null);
}
