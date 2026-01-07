import { apiClient } from './client.js';
import { store } from '../state/store.js';

export async function listContexts() {
  const state = store.getState();
  
  const options = {};
  if (state.authToken) {
    options.token = state.authToken;
  }
  
  try {
    const response = await apiClient.jsonRpcRequest('contexts.list', {}, crypto.randomUUID(), options);
    return Array.isArray(response) ? response : [];
  } catch (error) {
    console.error('Error loading contexts:', error);
    return [];
  }
}

export async function createContext(name = null) {
  const state = store.getState();
  
  const options = {};
  if (state.authToken) {
    options.token = state.authToken;
  }
  
  const payload = name ? { name } : {};
  return await apiClient.jsonRpcRequest('contexts.create', payload, crypto.randomUUID(), options);
}

export async function deleteContext(contextId) {
  const state = store.getState();
  
  const options = {};
  if (state.authToken) {
    options.token = state.authToken;
  }
  
  return await apiClient.jsonRpcRequest('contexts.delete', { contextId }, crypto.randomUUID(), options);
}

export async function switchContext(contextId) {
  store.setState({
    contextId,
    currentTaskId: null,
    currentTaskState: null
  });
}

export async function loadAndSetContexts() {
  const contexts = await listContexts();
  store.setState({ contexts });
  return contexts;
}
