import { store } from "../state/store.js";

export function showError(message) {
  store.setError(message);
}
