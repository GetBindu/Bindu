import { sendMessage } from "./chat/chat.js";
import { loadContexts } from "./contexts/contexts.js";
import { store } from "./state/store.js";
import { on } from "./core/events.js";
import { UI_FLAGS } from "./core/constants.js";

/* =========================
   DOM HELPERS
========================= */

function render(state) {
  const chat = document.getElementById("chat-messages");
  const indicator = document.getElementById("status-indicator");
  const error = document.getElementById("error");

  if (indicator) indicator.textContent = state.uiState.indicator || "";
  if (error) error.textContent = state.uiState.error || "";

  if (state.currentTaskState?.output) {
    const el = document.createElement("div");
    el.className = "message assistant";
    el.textContent = state.currentTaskState.output;
    chat.appendChild(el);
  }
}

/* =========================
   STORE SUBSCRIPTION
========================= */

store.subscribe(render);

/* =========================
   EVENTS
========================= */

on(UI_FLAGS.AUTH_REQUIRED, () => {
  store.setState({
    uiState: { modals: { auth: true } },
  });
});

on(UI_FLAGS.PAYMENT_REQUIRED, () => {
  store.setState({
    uiState: { modals: { payment: true } },
  });
});

/* =========================
   UI EVENTS
========================= */

document.getElementById("send-btn")?.addEventListener("click", () => {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  input.value = "";
  sendMessage(text);
});

/* =========================
   INIT
========================= */

loadContexts();
