import { agentAPI } from '$lib/services/agent-api';

export type VoiceState =
  | 'idle'
  | 'connecting'
  | 'active'
  | 'listening'
  | 'muted'
  | 'agent-speaking'
  | 'ended'
  | 'error';

export type TranscriptEvent = {
  role: 'user' | 'agent';
  text: string;
  isFinal: boolean;
  ts: number;
};

type VoiceSessionStart = {
  session_id: string;
  context_id: string;
  ws_url: string;
};

export class VoiceClient {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private state: VoiceState = 'idle';

  onTranscript?: (event: TranscriptEvent) => void;
  onAgentResponse?: (text: string) => void;
  onAgentAudio?: (audioData: ArrayBuffer) => void;
  onStateChange?: (state: VoiceState) => void;
  onError?: (message: string) => void;

  async startSession(contextId?: string): Promise<VoiceSessionStart> {
    const baseUrl = (agentAPI as unknown as { baseUrl?: string }).baseUrl || 'http://localhost:3773';
    let response: Response;
    try {
      response = await fetch(`${baseUrl}/voice/session/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(contextId ? { context_id: contextId } : {}),
      });
    } catch {
      throw new Error(`Cannot reach voice backend at ${baseUrl}. Is the agent running?`);
    }

    if (!response.ok) {
      const text = await response.text().catch(() => 'Unknown error');
      if (response.status === 404) {
        throw new Error(
          'Voice endpoint not found. Run a voice-enabled agent (examples/voice-agent/main.py).'
        );
      }
      throw new Error(`Failed to start voice session: ${response.status} ${text}`);
    }

    return response.json() as Promise<VoiceSessionStart>;
  }

  async connect(wsUrl: string, sessionId: string): Promise<void> {
    this.setState('connecting');
    this.sessionId = sessionId;

    await new Promise<void>((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);
      } catch (err) {
        reject(err);
        return;
      }

      if (!this.ws) {
        reject(new Error('WebSocket initialization failed'));
        return;
      }

      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        this.sendControl({ type: 'start', config: { sampleRate: 16000 } });
        this.setState('active');
        resolve();
      };

      this.ws.onerror = () => {
        this.setState('error');
        this.onError?.('Voice WebSocket connection error');
        reject(new Error('Voice WebSocket connection error'));
      };

      this.ws.onclose = () => {
        if (this.state !== 'ended' && this.state !== 'idle') {
          this.setState('ended');
        }
      };

      this.ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          this.onAgentAudio?.(event.data);
          return;
        }

        if (typeof event.data !== 'string') {
          return;
        }

        try {
          const data = JSON.parse(event.data) as {
            type?: string;
            role?: 'user' | 'agent';
            text?: string;
            is_final?: boolean;
            state?: VoiceState;
            message?: string;
          };

          if (data.type === 'transcript' && data.role && data.text) {
            this.onTranscript?.({
              role: data.role,
              text: data.text,
              isFinal: Boolean(data.is_final ?? true),
              ts: Date.now(),
            });
            return;
          }

          if (data.type === 'agent_response' && data.text) {
            this.onAgentResponse?.(data.text);
            return;
          }

          if (data.type === 'state' && data.state) {
            this.setState(data.state);
            return;
          }

          if (data.type === 'error' && data.message) {
            this.setState('error');
            this.onError?.(data.message);
          }
        } catch {
          // Ignore malformed frames
        }
      };
    });
  }

  async sendUserText(text: string): Promise<void> {
    if (!text.trim()) {
      return;
    }
    this.sendControl({ type: 'user_text', text: text.trim() });
  }

  commitTurn(): void {
    this.sendControl({ type: 'commit_turn' });
  }

  mute(): void {
    if (this.sendControl({ type: 'mute' })) {
      this.setState('muted');
    }
  }

  unmute(): void {
    if (this.sendControl({ type: 'unmute' })) {
      this.setState('listening');
    }
  }

  async stopSession(): Promise<void> {
    const id = this.sessionId;
    this.sendControl({ type: 'stop' });

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.sessionId = null;
    this.setState('ended');

    if (id) {
      const baseUrl = (agentAPI as unknown as { baseUrl?: string }).baseUrl || 'http://localhost:3773';
      await fetch(`${baseUrl}/voice/session/${id}`, { method: 'DELETE' }).catch(() => undefined);
    }
  }

  private sendControl(payload: Record<string, unknown>): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    this.ws.send(JSON.stringify(payload));
    return true;
  }

  private setState(state: VoiceState): void {
    this.state = state;
    this.onStateChange?.(state);
  }
}
