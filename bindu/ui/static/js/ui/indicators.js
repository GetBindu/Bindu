import { store } from "../state/store.js";

export function showIndicator(text) {
  store.setIndicator(text);
}

export function clearIndicator() {
  store.setIndicator(null);
}
