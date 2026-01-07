import { listContexts, createContext, deleteContext, switchContext } from "../api/contexts.js";
import { store } from "../state/store.js";

export async function loadContexts() {
  try {
    const contexts = await listContexts();
    store.setState({ contexts });
  } catch (error) {
    store.setError("Failed to load contexts");
  }
}

export async function createNewContext(name = null) {
  try {
    const newContext = await createContext(name);
    await loadContexts();
    return newContext;
  } catch (error) {
    store.setError("Failed to create context");
    throw error;
  }
}

export async function removeContext(contextId) {
  try {
    await deleteContext(contextId);
    await loadContexts();
  } catch (error) {
    store.setError("Failed to delete context");
    throw error;
  }
}

export function setActiveContext(contextId) {
  switchContext(contextId);
}
