// Centralized application state (Phase 2 + 2.5)

const initialState = {
  // Agent
  agentInfo: null,

  // Auth & Payment
  authToken: null,
  paymentToken: null,

  // Task lifecycle
  currentTaskId: null,
  currentTaskState: null,
  taskHistory: [],

  // Contexts
  contextId: null,
  contexts: [],

  // UI
  uiState: {
    activeTab: "chat",
    modals: {
      auth: false,
      payment: false,
      feedback: false,
      skill: null,
    },
    loading: false,
    error: null,
    indicator: null, // 👈 Phase 2.5
  },
};

let state = structuredClone(initialState);
const listeners = new Set();

/* =========================
   Core Store API
========================= */

function getState() {
  return structuredClone(state);
}

function setState(partial) {
  state = {
    ...state,
    ...partial,
    uiState: {
      ...state.uiState,
      ...(partial.uiState || {}),
    },
  };

  listeners.forEach((fn) => fn(getState()));
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function resetState() {
  state = structuredClone(initialState);
  listeners.forEach((fn) => fn(getState()));
}

/* =========================
   Phase 2 Helpers (SAFE)
========================= */

function setLoading(isLoading) {
  setState({
    uiState: {
      loading: isLoading,
    },
  });
}

function setError(error) {
  setState({
    uiState: {
      error,
      loading: false,
    },
  });
}

function setIndicator(text) {
  setState({
    uiState: {
      indicator: text,
    },
  });
}

function clearIndicator() {
  setState({
    uiState: {
      indicator: null,
    },
  });
}

function updateTask(task) {
  setState({
    currentTaskId: task?.id ?? null,
    currentTaskState: task,
    taskHistory: task
      ? [...state.taskHistory, task]
      : state.taskHistory,
  });
}

/* =========================
   Export
========================= */

export const store = {
  // Phase 1 API (unchanged)
  getState,
  setState,
  subscribe,
  resetState,

  // Phase 2 helpers
  setLoading,
  setError,
  setIndicator,
  clearIndicator,
  updateTask,
};
