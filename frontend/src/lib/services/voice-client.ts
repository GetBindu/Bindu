import { getAgentBaseUrl } from "$lib/services/agent-api";

export type VoiceState =
	| "idle"
	| "connecting"
	| "active"
	| "listening"
	| "muted"
	| "agent-speaking"
	| "ended"
	| "error";

export type TranscriptEvent = {
	role: "user" | "agent";
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
	private state: VoiceState = "idle";
	private mediaStream: MediaStream | null = null;
	private audioContext: AudioContext | null = null;
	private sourceNode: MediaStreamAudioSourceNode | null = null;
	private processorNode: AudioWorkletNode | null = null;
	private silentGainNode: GainNode | null = null;
	private isStreamingAudio = false;
	private pendingConnectResolve: (() => void) | null = null;
	private pendingConnectReject: ((reason?: unknown) => void) | null = null;
	private duplexHoldUntilMs = 0;
	private isStopping = false;
	private stopToken = 0;

	private extendDuplexHold(ms: number): void {
		this.duplexHoldUntilMs = Math.max(this.duplexHoldUntilMs, Date.now() + ms);
	}

	holdMicFor(ms: number): void {
		if (ms <= 0) {
			return;
		}
		this.extendDuplexHold(ms);
	}

	onTranscript?: (event: TranscriptEvent) => void;
	onAgentResponse?: (text: string) => void;
	onAgentAudio?: (audioData: ArrayBuffer) => void;
	onStateChange?: (state: VoiceState) => void;
	onError?: (message: string) => void;

	async startSession(contextId?: string): Promise<VoiceSessionStart> {
		const baseUrl = getAgentBaseUrl();
		let response: Response;
		try {
			response = await fetch(`${baseUrl}/voice/session/start`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(contextId ? { context_id: contextId } : {}),
			});
		} catch {
			throw new Error(`Cannot reach voice backend at ${baseUrl}. Is the agent running?`);
		}

		if (!response.ok) {
			const text = await response.text().catch(() => "Unknown error");
			if (response.status === 404) {
				throw new Error(
					"Voice endpoint not found. Run a voice-enabled agent (examples/voice-agent/main.py)."
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
		this.setState("connecting");
		this.sessionId = sessionId;
		const voiceWsSubprotocol = "bindu.voice.v1";

		await new Promise<void>((resolve, reject) => {
			this.pendingConnectResolve = resolve;
			this.pendingConnectReject = reject;
			try {
				const resolved = this.resolveWebSocketUrl(wsUrl);
				// Negotiate the fixed voice subprotocol and pass the session token as
				// the second subprotocol item so the backend can validate both parts.
				this.ws = sessionToken
					? new WebSocket(resolved, [voiceWsSubprotocol, sessionToken])
					: new WebSocket(resolved);
			} catch (err) {
				this.pendingConnectResolve = null;
				this.pendingConnectReject = null;
				reject(err);
				return;
			}

			if (!this.ws) {
				this.pendingConnectResolve = null;
				this.pendingConnectReject = null;
				reject(new Error("WebSocket initialization failed"));
				return;
			}

			this.ws.binaryType = "arraybuffer";

			this.ws.onopen = () => {
				this.isStopping = false;
				this.pendingConnectResolve = null;
				this.pendingConnectReject = null;
				this.sendControl({ type: "start", config: { sampleRate: 16000 } });
				this.setState("active");
				resolve();
			};

			this.ws.onerror = () => {
				this.pendingConnectResolve = null;
				this.pendingConnectReject = null;
				this.setState("error");
				this.onError?.("Voice WebSocket connection error");
				reject(new Error("Voice WebSocket connection error"));
			};

			this.ws.onclose = () => {
				if (this.pendingConnectReject) {
					this.pendingConnectReject(new Error("WebSocket closed before open"));
					this.pendingConnectResolve = null;
					this.pendingConnectReject = null;
				}
				this.cleanupAudioStreaming();
				if (this.state !== "ended" && this.state !== "idle") {
					this.setState("ended");
				}
			};

			this.ws.onmessage = (event) => {
				if (event.data instanceof ArrayBuffer) {
					// While agent audio is arriving, hold mic uplink briefly to avoid
					// speaker-to-mic feedback loops.
					this.extendDuplexHold(1800);
					this.onAgentAudio?.(event.data);
					return;
				}

				if (typeof event.data !== "string") {
					return;
				}

				try {
					const data = JSON.parse(event.data) as {
						type?: string;
						role?: "user" | "agent";
						text?: string;
						is_final?: boolean;
						state?: VoiceState;
						message?: string;
					};

					if (data.type === "transcript" && data.role && data.text) {
						if (data.role === "agent") {
							this.extendDuplexHold(data.is_final ? 1800 : 2600);
						}
						this.onTranscript?.({
							role: data.role,
							text: data.text,
							isFinal: Boolean(data.is_final ?? true),
							ts: Date.now(),
						});
						return;
					}

					if (data.type === "agent_response" && data.text) {
						this.extendDuplexHold(1800);
						this.onAgentResponse?.(data.text);
						return;
					}

					if (data.type === "state" && data.state) {
						this.setState(data.state);
						return;
					}

					if (data.type === "error" && data.message) {
						this.setState("error");
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
		this.sendControl({ type: "user_text", text: text.trim() });
	}

	commitTurn(): void {
		this.sendControl({ type: "commit_turn" });
	}

	mute(): void {
		if (this.sendControl({ type: "mute" })) {
			this.setState("muted");
		}
	}

	unmute(): void {
		if (this.sendControl({ type: "unmute" })) {
			this.setState("listening");
		}
	}

	async stopSession(): Promise<void> {
		this.isStopping = true;
		this.stopToken += 1;
		const id = this.sessionId;
		this.sendControl({ type: "stop" });
		this.cleanupAudioStreaming();

		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}

		this.sessionId = null;
		this.setState("ended");

		if (id) {
			const baseUrl = getAgentBaseUrl();
			await fetch(`${baseUrl}/voice/session/${id}`, { method: "DELETE" }).catch(() => undefined);
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
		if (state === "agent-speaking") {
			this.extendDuplexHold(2500);
		} else if (state === "listening") {
			this.extendDuplexHold(800);
		}
		this.onStateChange?.(state);
	}

	private canSendMicAudio(): boolean {
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			return false;
		}
		if (this.state === "muted" || this.state === "agent-speaking") {
			return false;
		}
		return Date.now() >= this.duplexHoldUntilMs;
	}

	async startAudioStreaming(): Promise<void> {
		if (this.isStreamingAudio) {
			return;
		}

		if (this.isStopping || !this.sessionId) {
			return;
		}

		const setupToken = this.stopToken;

		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			throw new Error("Voice WebSocket is not connected");
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

		if (this.isStopping || setupToken !== this.stopToken || !this.sessionId) {
			stream.getTracks().forEach((track) => track.stop());
			return;
		}

		const AudioContextCtor =
			window.AudioContext ||
			(window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

		if (!AudioContextCtor) {
			stream.getTracks().forEach((track) => track.stop());
			throw new Error("AudioContext is not supported in this browser");
		}

		const desiredSampleRate = 16000;
		const audioContext = new AudioContextCtor({ sampleRate: desiredSampleRate });
		await audioContext.resume();

		if (this.isStopping || setupToken !== this.stopToken || !this.sessionId) {
			void audioContext.close();
			stream.getTracks().forEach((track) => track.stop());
			return;
		}

		// Inline AudioWorkletProcessor code to avoid external file dependencies
		const workletCode = `
      class PCM16Processor extends AudioWorkletProcessor {
        constructor() {
          super();
          this.buffer = new Float32Array(4096);
          this.bufferIndex = 0;
        }

        process(inputs, outputs, parameters) {
          const input = inputs[0];
          if (!input || !input[0]) return true;

          const channelData = input[0];

          for (let i = 0; i < channelData.length; i++) {
            this.buffer[this.bufferIndex++] = channelData[i];
            if (this.bufferIndex >= this.buffer.length) {
              this.flushBuffer();
            }
          }

          return true;
        }

        flushBuffer() {
          const pcm16 = new Int16Array(this.bufferIndex);
          for (let j = 0; j < this.bufferIndex; j++) {
            const s = Math.max(-1, Math.min(1, this.buffer[j]));
            pcm16[j] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
          this.bufferIndex = 0;
        }
      }
      registerProcessor('pcm16-processor', PCM16Processor);
    `;

		const blob = new Blob([workletCode], { type: "application/javascript" });
		const workletUrl = URL.createObjectURL(blob);

		try {
			await audioContext.audioWorklet.addModule(workletUrl);
		} finally {
			URL.revokeObjectURL(workletUrl);
		}

		if (this.isStopping || setupToken !== this.stopToken || !this.sessionId) {
			void audioContext.close();
			stream.getTracks().forEach((track) => track.stop());
			return;
		}

		const sourceNode = audioContext.createMediaStreamSource(stream);
		const workletNode = new AudioWorkletNode(audioContext, "pcm16-processor");
		const silentGainNode = audioContext.createGain();
		silentGainNode.gain.value = 0;

		workletNode.port.onmessage = (event) => {
			if (!this.canSendMicAudio()) {
				return;
			}
			const ws = this.ws;
			if (!ws || ws.readyState !== WebSocket.OPEN) {
				return;
			}
			ws.send(event.data);
		};

		sourceNode.connect(workletNode);
		workletNode.connect(silentGainNode);
		silentGainNode.connect(audioContext.destination);

		if (this.isStopping || setupToken !== this.stopToken || !this.sessionId) {
			workletNode.disconnect();
			silentGainNode.disconnect();
			sourceNode.disconnect();
			void audioContext.close();
			stream.getTracks().forEach((track) => track.stop());
			return;
		}

		this.mediaStream = stream;
		this.audioContext = audioContext;
		this.sourceNode = sourceNode;
		this.processorNode = workletNode;
		this.silentGainNode = silentGainNode;
		this.isStreamingAudio = true;
	}

	stopAudioStreaming(): void {
		this.cleanupAudioStreaming();
		this.commitTurn();
	}

	private cleanupAudioStreaming(): void {
		this.stopToken += 1;
		this.isStreamingAudio = false;

		if (this.processorNode) {
			this.processorNode.disconnect();
			this.processorNode.port.onmessage = null;
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
		const configuredBaseUrl = getAgentBaseUrl().replace(/^http/, "ws");

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
