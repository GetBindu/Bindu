// bindu/ui/static/js/api/client.js
import { CONFIG } from '../config.js';

export class ApiError extends Error {
  constructor(message, status = null, payload = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

class ApiClient {
  constructor(baseURL = CONFIG.BASE_URL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${this.baseURL}${endpoint}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      CONFIG.TIMEOUTS.REQUEST_TIMEOUT
    );

    // Destructure special options so they don't get passed to fetch directly
    const { token, paymentToken, headers = {}, ...fetchOptions } = options;

    // 1. Build Headers
    const finalHeaders = {
        'Content-Type': 'application/json',
        ...headers
    };

    // 2. Inject Auth Token
    if (token) {
        const cleanToken = token.trim();
        if (/^[\x00-\x7F]*$/.test(cleanToken)) {
            finalHeaders['Authorization'] = `Bearer ${cleanToken}`;
        }
    }

    // 3. Inject Payment Token
    if (paymentToken) {
        const cleanToken = paymentToken.trim();
        if (/^[\x00-\x7F]*$/.test(cleanToken)) {
            finalHeaders['X-PAYMENT'] = cleanToken;
        }
    }

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers: finalHeaders,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let payload = null;
        try { payload = await response.json(); } catch { /* ignore */ }

        throw new ApiError(
          payload?.message || response.statusText,
          response.status,
          payload
        );
      }

      try {
        return await response.json();
      } catch {
        return null;
      }

    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') throw new ApiError('Request timeout');
      if (error instanceof ApiError) throw error;
      throw new ApiError(error.message || 'Network error');
    }
  }

  // Updated to accept options (4th argument)
  async jsonRpcRequest(method, params = {}, id = crypto.randomUUID(), options = {}) {
    const response = await this.request(CONFIG.ENDPOINTS.JSON_RPC, {
      method: 'POST',
      ...options, // Pass token/paymentToken down to request
      body: JSON.stringify({
        jsonrpc: '2.0',
        method,
        params,
        id
      })
    });

    if (response?.error) {
      throw new ApiError(
        response.error.message || 'JSON-RPC error',
        null,
        response.error
      );
    }

    return response?.result ?? null;
  }
}

export const apiClient = new ApiClient();