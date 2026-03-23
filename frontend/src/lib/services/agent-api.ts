import type {
  JSONRPCRequest,
  JSONRPCResponse,
  Task,
  Context,
  SendMessageParams
} from '$lib/types/agent';

export class AgentAPIError extends Error {
  constructor(
    message: string,
    public code?: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'AgentAPIError';
  }
}

export class AgentAPI {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string = '') {
    // Use BINDU_BASE_URL from env or default to localhost:3773
    this.baseUrl = baseUrl || 'http://localhost:3773';
    console.log('AgentAPI initialized with baseUrl:', this.baseUrl);
  }

  setAuthToken(token: string | null) {
    console.log('AgentAPI.setAuthToken called with:', token ? `${token.substring(0, 20)}...` : 'null');
    this.authToken = token;
    console.log('Token stored in AgentAPI instance:', this.authToken ? 'YES' : 'NO');

    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('bindu_oauth_token', token);
      } else {
        localStorage.removeItem('bindu_oauth_token');
      }
    }
  }

  getAuthToken(): string | null {
    if (!this.authToken && typeof window !== 'undefined') {
      this.authToken = localStorage.getItem('bindu_oauth_token');
    }
    return this.authToken;
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    const token = this.getAuthToken();
    console.log('getHeaders - token retrieved:', token ? `${token.substring(0, 30)}...` : 'NULL');
    console.log('getHeaders - this.authToken:', this.authToken ? `${this.authToken.substring(0, 30)}...` : 'NULL');
    console.log('getHeaders - localStorage token:', typeof window !== 'undefined' ? localStorage.getItem('bindu_oauth_token')?.substring(0, 30) + '...' : 'N/A');

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
      console.log('✅ Authorization header added');
    } else {
      console.error('❌ NO TOKEN - Authorization header NOT added');
    }

    return headers;
  }

  private async request<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    const requestId = crypto.randomUUID();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Only add Authorization header if token exists (auth is optional)
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    const body = {
      jsonrpc: '2.0',
      method,
      params,
      id: requestId,
    };

    console.log('=== Agent API Request ===');
    console.log('URL:', this.baseUrl);
    console.log('Method:', method);
    console.log('Headers:', headers);
    console.log('Auth token:', this.authToken || 'none (optional)');
    console.log('Request body:', body);

    const response = await fetch(this.baseUrl + '/', {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });

    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));

    if (response.status === 401) {
      throw new AgentAPIError('Authentication required', 401);
    }

    if (response.status === 402) {
      throw new AgentAPIError('Payment required', 402);
    }

    if (!response.ok) {
      throw new AgentAPIError(`HTTP ${response.status}: ${response.statusText}`, response.status);
    }

    const result: JSONRPCResponse<T> = await response.json();

    if (result.error) {
      throw new AgentAPIError(
        result.error.message || 'Unknown error',
        result.error.code,
        result.error.data
      );
    }

    if (!result.result) {
      throw new AgentAPIError('No result in response');
    }

    return result.result;
  }

  async sendMessage(params: SendMessageParams): Promise<Task> {
    return this.request<Task>('message/send', params);
  }

  async getTask(taskId: string): Promise<Task> {
    return this.request<Task>('tasks/get', { taskId });
  }

  async listContexts(length?: number, offset?: number): Promise<Context[]> {
    const params: Record<string, unknown> = {};
    if (length !== undefined) params.length = length;
    if (offset !== undefined) params.offset = offset;
    return this.request<Context[]>('contexts/list', params);
  }

  async listTasks(): Promise<Task[]> {
    return this.request<Task[]>('tasks/list', {});
  }

  async clearContext(contextId: string): Promise<void> {
    await this.request<void>('contexts/clear', { contextId });
  }

  async submitFeedback(taskId: string, rating: number, feedback?: string): Promise<void> {
    const params: Record<string, unknown> = { taskId, rating };
    if (feedback) params.feedback = feedback;
    await this.request<void>('tasks/feedback', params);
  }

  /**
   * Send a message and get streaming response compatible with existing MessageUpdate format
   */
  async *sendMessageStream(
    message: string,
    contextId?: string,
    abortSignal?: AbortSignal
  ): AsyncGenerator<{ type: 'stream' | 'status' | 'finalAnswer'; token?: string; status?: string }> {
    const response = await fetch(`${this.baseUrl}/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'message/send',
        params: {
          message,
          contextId: contextId || undefined,
        },
        id: crypto.randomUUID(),
      }),
      signal: abortSignal,
    });

    if (!response.ok) {
      throw new Error(`Agent API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    if (data.error) {
      yield { type: 'status', status: 'error' };
      throw new Error(data.error.message || 'Agent API error');
    }

    // Emit the response as stream tokens
    if (data.result?.response) {
      const text = data.result.response;
      // Split into chunks to simulate streaming
      const chunkSize = 5;
      for (let i = 0; i < text.length; i += chunkSize) {
        yield { type: 'stream', token: text.slice(i, i + chunkSize) };
      }
    }

    yield { type: 'finalAnswer' };
  }
}

export const agentAPI = new AgentAPI();
