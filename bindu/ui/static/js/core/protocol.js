import { TASK_STATUS, UI_FLAGS } from "./constants.js";

export function parseTaskResponse(payload) {
  if (!payload || typeof payload !== "object") {
    return { error: "Invalid response format" };
  }

  if (payload.flag === UI_FLAGS.AUTH_REQUIRED) {
    return { uiFlag: UI_FLAGS.AUTH_REQUIRED };
  }

  if (payload.flag === UI_FLAGS.PAYMENT_REQUIRED) {
    return { uiFlag: UI_FLAGS.PAYMENT_REQUIRED };
  }

  if (!payload.task || typeof payload.task !== "object") {
    return { error: "Missing task object" };
  }

  if (!Object.values(TASK_STATUS).includes(payload.task.status)) {
    return { error: "Unknown task status" };
  }

  return { task: payload.task };
}
