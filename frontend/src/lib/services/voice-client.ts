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
  session_token?: string;
};

export class VoiceClient {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private state: VoiceState = 'idle';
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private processorNode: ScriptProcessorNode | null = null;
  private silentGainNode: GainNode | null = null;
  private isStreamingAudio = false;
  private pendingConnectResolve: (() => void) | null = null;
  private pendingConnectReject: ((reason?: unknown) => void) | null = null;

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

    try {
      return (await response.json()) as VoiceSessionStart;
    } catch (err) {
      throw new Error(
        `Failed to parse voice session response: ${err instanceof Error ? err.message : String(err)}`
      );
    }
  }

  async connect(wsUrl: string, sessionId: string, sessionToken?: string): Promise<void> {
    this.setState('connecting');
    this.sessionId = sessionId;

    await new Promise<void>((resolve, reject) => {
      this.pendingConnectResolve = resolve;
      this.pendingConnectReject = reject;
      try {
        const resolved = this.resolveWebSocketUrl(wsUrl);
        // If the backend requires session auth, it expects the token either as:
        // - Sec-WebSocket-Protocol header (preferred), or
        // - first text frame after connect (fallback).
        this.ws = sessionToken ? new WebSocket(resolved, [sessionToken]) : new WebSocket(resolved);
      } catch (err) {
        this.pendingConnectResolve = null;
        this.pendingConnectReject = null;
        reject(err);
        return;
      }

      if (!this.ws) {
        this.pendingConnectResolve = null;
        this.pendingConnectReject = null;
        reject(new Error('WebSocket initialization failed'));
        return;
      }

      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        this.pendingConnectResolve = null;
        this.pendingConnectReject = null;
        if (sessionToken) {
          // Only send the token as a first text frame if subprotocol negotiation
          // did not succeed. Otherwise the server will treat this as a malformed
          // JSON control frame and close the connection.
          const negotiatedProtocol = this.ws?.protocol;
          if (!negotiatedProtocol) {
            try {
              this.ws?.send(sessionToken);
            } catch {
              // Ignore and proceed; server may already have token via headers.
            }
          }
        }
        this.sendControl({ type: 'start', config: { sampleRate: 16000 } });
        this.setState('active');
        resolve();
      };

      this.ws.onerror = () => {
        this.pendingConnectResolve = null;
        this.pendingConnectReject = null;
        this.setState('error');
        this.onError?.('Voice WebSocket connection error');
        reject(new Error('Voice WebSocket connection error'));
      };

      this.ws.onclose = () => {
        if (this.pendingConnectReject) {
          this.pendingConnectReject(new Error('WebSocket closed before open'));
          this.pendingConnectResolve = null;
          this.pendingConnectReject = null;
        }
        this.cleanupAudioStreaming();
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
    this.cleanupAudioStreaming();

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

  async startAudioStreaming(): Promise<void> {
    if (this.isStreamingAudio) {
      return;
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('Voice WebSocket is not connected');
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextCtor =
      window.AudioContext ||
      (window as typeof window & { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;

    if (!AudioContextCtor) {
      stream.getTracks().forEach((track) => track.stop());
      throw new Error('AudioContext is not supported in this browser');
    }

    const desiredSampleRate = 16000;
    const audioContext = new AudioContextCtor({ sampleRate: desiredSampleRate });
    await audioContext.resume();
    const actualSampleRate = audioContext.sampleRate;

    const resampleState =
      actualSampleRate === desiredSampleRate
        ? null
        : { t: 0, lastSample: 0, ratio: actualSampleRate / desiredSampleRate };

    const resampleChunk = (
      input: Float32Array,
      state: { t: number; lastSample: number; ratio: number }
    ): Float32Array => {
      const ratio = state.ratio;
      if (!Number.isFinite(ratio) || ratio <= 0) {
        return input;
      }

      const estimatedLength = Math.floor((input.length - state.t) / ratio);
      const outputLength = Math.max(0, estimatedLength);
      const output = new Float32Array(outputLength);

      for (let i = 0; i < outputLength; i += 1) {
        const idx = state.t;
        const i0 = Math.floor(idx);
        const frac = idx - i0;

        const s0 = i0 >= 0 ? (input[i0] ?? 0) : state.lastSample;
        const s1 = input[i0 + 1] ?? input[input.length - 1] ?? s0;
        output[i] = s0 + (s1 - s0) * frac;

        state.t += ratio;
      }

      state.lastSample = input[input.length - 1] ?? state.lastSample;
      state.t -= input.length;
      return output;
    };
    const sourceNode = audioContext.createMediaStreamSource(stream);
    const processorNode = audioContext.createScriptProcessor(4096, 1, 1);
    const silentGain = audioContext.createGain();
    silentGain.gain.value = 0;

    processorNode.onaudioprocess = (event) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN || this.state === 'muted') {
        return;
      }

      const inputData = event.inputBuffer.getChannelData(0);
      const floatChunk = resampleState ? resampleChunk(inputData, resampleState) : inputData;
      const pcmChunk = convertFloat32ToPcm16(floatChunk);
      if (pcmChunk.byteLength > 0) {
        this.ws.send(pcmChunk);
      }
    };

    sourceNode.connect(processorNode);
    processorNode.connect(silentGain);
    silentGain.connect(audioContext.destination);

    this.mediaStream = stream;
    this.audioContext = audioContext;
    this.sourceNode = sourceNode;
    this.processorNode = processorNode;
    this.silentGainNode = silentGain;
    this.isStreamingAudio = true;
  }

  stopAudioStreaming(): void {
    this.cleanupAudioStreaming();
    this.commitTurn();
  }

  private cleanupAudioStreaming(): void {
    this.isStreamingAudio = false;

    if (this.processorNode) {
      this.processorNode.disconnect();
      this.processorNode.onaudioprocess = null;
      this.processorNode = null;
    }

    if (this.silentGainNode) {
      this.silentGainNode.disconnect();
      this.silentGainNode = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.audioContext) {
      void this.audioContext.close();
      this.audioContext = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
  }

  private resolveWebSocketUrl(wsUrl: string): string {
    const configuredBaseUrl = (
      (agentAPI as unknown as { baseUrl?: string }).baseUrl || 'http://localhost:3773'
    ).replace(/^http/, 'ws');

    try {
      const endpointUrl = new URL(wsUrl);
      const proxyBaseUrl = new URL(configuredBaseUrl);
      endpointUrl.protocol = proxyBaseUrl.protocol;
      endpointUrl.host = proxyBaseUrl.host;
      return endpointUrl.toString();
    } catch {
      return wsUrl;
    }
  }
}

function convertFloat32ToPcm16(input: Float32Array): ArrayBuffer {
  const pcm = new Int16Array(input.length);
  for (let index = 0; index < input.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, input[index] ?? 0));
    pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return pcm.buffer;
}
