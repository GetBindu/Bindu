// Simple event bus (Phase 2.5)

const listeners = new Map();

export function on(event, handler) {
  if (!listeners.has(event)) {
    listeners.set(event, new Set());
  }
  listeners.get(event).add(handler);

  return () => listeners.get(event)?.delete(handler);
}

export function emit(event, payload) {
  if (!listeners.has(event)) return;
  listeners.get(event).forEach(fn => fn(payload));
}
