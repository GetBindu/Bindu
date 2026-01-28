import { store } from "../state/store.js";

export async function apiFetch(url, options = {}) {
  const { authToken, paymentToken } = store.getState();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  if (paymentToken) {
    headers["X-Payment-Token"] = paymentToken;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  return response
}
