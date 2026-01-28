import { apiFetch } from "../core/api.js";
import { parseTaskResponse } from "../core/protocol.js";
import { applyTask } from "../tasks/tasks.js";
import { store } from "../state/store.js";
import { emit } from "../core/events.js";
import { A2A_ENDPOINTS } from "../core/constants.js";

export async function sendMessage(text) {
  if (!text || typeof text !== "string") return;

  emit("task:started");
  store.setIndicator("🤖 Agent is thinking…");

  try {
    const res = await apiFetch(A2A_ENDPOINTS.A2A, {
      method: "POST",
      body: JSON.stringify({ input: text }),
    });

    const payload = await res.json();
    const parsed = parseTaskResponse(payload);

    if (parsed.uiFlag) {
      store.setIndicator(null);
      emit(parsed.uiFlag);
      return;
    }

    if (parsed.error) {
      store.setError(parsed.error);
      return;
    }

    applyTask(parsed.task);
  } catch {
    store.setError("Network error");
  } finally {
    store.setIndicator(null);
  }
}
