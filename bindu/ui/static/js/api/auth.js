import { store } from '../state/store.js';
import { storage, STORAGE_KEYS } from '../utils/storage.js';

export function setAuthToken(token) {
  const cleanToken = token ? token.trim() : null;
  
  if (cleanToken && !/^[\x00-\x7F]*$/.test(cleanToken)) {
    throw new Error('Auth token contains non-ASCII characters');
  }
  
  store.setState({ authToken: cleanToken });
  
  if (cleanToken) {
    storage.setAuthToken(cleanToken);
  } else {
    storage.clearAuthToken();
  }
  
  return cleanToken;
}

export function getAuthToken() {
  const state = store.getState();
  return state.authToken || storage.getAuthToken();
}

export function clearAuthToken() {
  store.setState({ authToken: null });
  storage.clearAuthToken();
}

export function validateToken(token) {
  if (!token) return false;
  const cleanToken = token.trim();
  return /^[\x00-\x7F]*$/.test(cleanToken);
}

export function initializeAuth() {
  const storedToken = storage.getAuthToken();
  if (storedToken && validateToken(storedToken)) {
    store.setState({ authToken: storedToken });
  }
}
