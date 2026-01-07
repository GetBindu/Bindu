import { createTask } from "../api/tasks.js";
import { handlePaymentFlow } from "../api/payment.js";
import { parseTaskResponse } from "../core/protocol.js";
import { applyTask } from "../tasks/tasks.js";
import { store } from "../state/store.js";
import { emit } from "../core/events.js";
import { UI_FLAGS } from "../core/constants.js";
import { ApiError } from "../api/client.js";

export async function sendMessage(text) {
  if (!text || typeof text !== "string") return;

  emit("task:started");
  store.setIndicator("🤖 Agent is thinking…");

  try {
    const result = await createTask(text);
    const parsed = parseTaskResponse(result);

    if (parsed.uiFlag) {
      store.clearIndicator();
      
      if (parsed.uiFlag === UI_FLAGS.PAYMENT_REQUIRED) {
        try {
          store.setIndicator("💰 Processing payment...");
          const paymentResult = await handlePaymentFlow();
          
          if (paymentResult.success) {
            store.setIndicator("✅ Payment complete! Retrying...");
            return await sendMessage(text);
          }
        } catch (error) {
          store.setError(`Payment failed: ${error.message}`);
          return;
        }
      }
      
      emit(parsed.uiFlag);
      return;
    }

    if (parsed.error) {
      store.setError(parsed.error);
      return;
    }

    applyTask(parsed.task);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        emit(UI_FLAGS.AUTH_REQUIRED);
      } else if (error.status === 402) {
        emit(UI_FLAGS.PAYMENT_REQUIRED);
      } else {
        store.setError(error.message || "Request failed");
      }
    } else {
      store.setError("Network error");
    }
  } finally {
    store.clearIndicator();
  }
}
