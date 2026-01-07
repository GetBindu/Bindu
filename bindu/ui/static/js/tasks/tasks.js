import { store } from "../state/store.js";
import { emit } from "../core/events.js";
import { submitTaskFeedback, cancelTask as apiCancelTask } from "../api/tasks.js";

export function applyTask(task) {
  store.updateTask(task);
  emit("task:updated", task);
}

export function clearTask() {
  store.updateTask(null);
}

export async function submitFeedback(taskId, rating, feedback = '') {
  try {
    await submitTaskFeedback(taskId, rating, feedback);
    return true;
  } catch (error) {
    console.error('Failed to submit feedback:', error);
    throw error;
  }
}

export async function cancelTask(taskId) {
  try {
    await apiCancelTask(taskId);
    clearTask();
    return true;
  } catch (error) {
    console.error('Failed to cancel task:', error);
    throw error;
  }
}
