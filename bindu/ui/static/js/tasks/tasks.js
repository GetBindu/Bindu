import { store } from "../state/store.js";
import { emit } from "../core/events.js";

export function applyTask(task) {
  store.updateTask(task);
  emit("task:updated", task);
}

export function clearTask() {
  store.updateTask(null);
}
