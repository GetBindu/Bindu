import { apiFetch } from "../core/api.js";
import { store } from "../state/store.js";
import { A2A_ENDPOINTS } from "../core/constants.js";

export async function loadContexts() {
  try {
    const res = await apiFetch(A2A_ENDPOINTS.TASKS);
    const data = await res.json();

    store.setState({
      contexts: Array.isArray(data) ? data : [],
    });
  } catch {
    store.setError("Failed to load contexts");
  }
}

export function setActiveContext(id) {
  store.setState({
    contextId: id,
    currentTaskId: null,
    currentTaskState: null,
  });
}
