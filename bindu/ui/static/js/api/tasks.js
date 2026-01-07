import { apiClient } from './client.js';
import { CONFIG } from '../config.js';
import { store } from '../state/store.js';

export async function createTask(input, options = {}) {
  const state = store.getState();
  const { contextId, currentTaskId, currentTaskState } = state;
  
  const payload = {
    input,
    contextId: contextId || undefined
  };
  
  if (currentTaskId && currentTaskState) {
    const isTerminal = ['completed', 'failed', 'canceled'].includes(currentTaskState.status);
    
    if (isTerminal) {
      payload.referenceTaskIds = [currentTaskId];
    } else {
      payload.taskId = currentTaskId;
    }
  }
  
  const requestOptions = {
    method: 'POST',
    body: JSON.stringify(payload),
    ...options
  };
  
  if (state.authToken) {
    requestOptions.token = state.authToken;
  }
  
  if (state.paymentToken) {
    requestOptions.paymentToken = state.paymentToken;
  }
  
  return await apiClient.jsonRpcRequest('tasks.create', payload, crypto.randomUUID(), requestOptions);
}

export async function getTaskStatus(taskId, options = {}) {
  const state = store.getState();
  
  const requestOptions = { ...options };
  
  if (state.authToken) {
    requestOptions.token = state.authToken;
  }
  
  if (state.paymentToken) {
    requestOptions.paymentToken = state.paymentToken;
  }
  
  return await apiClient.jsonRpcRequest('tasks.status', { taskId }, crypto.randomUUID(), requestOptions);
}

export async function submitTaskFeedback(taskId, rating, feedback = '') {
  const payload = {
    taskId,
    rating: parseInt(rating, 10),
    feedback: feedback.trim()
  };
  
  return await apiClient.jsonRpcRequest('tasks.feedback', payload);
}

export async function cancelTask(taskId) {
  return await apiClient.jsonRpcRequest('tasks.cancel', { taskId });
}
