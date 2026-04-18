import { get, writable } from "svelte/store";
import { VoiceClient, type TranscriptEvent, type VoiceState } from "../services/voice-client";

export type VoiceTranscript = TranscriptEvent & { id: string };

export const voiceSessionId = writable<string | null>(null);
export const voiceContextId = writable<string | null>(null);
export const voiceState = writable<VoiceState>("idle");
export const isVoiceMuted = writable<boolean>(false);
export const transcripts = writable<VoiceTranscript[]>([]);
export const currentUserTranscript = writable<string>("");
export const currentAgentTranscript = writable<string>("");
export const latestAgentAudio = writable<ArrayBuffer | null>(null);
export const voiceError = writable<string | null>(null);

let client: VoiceClient | null = null;
let isStarting = false;
let startTokenCounter = 0;
let transcriptIdCounter = 0;

function resetVoiceCallState(): void {
	isVoiceMuted.set(false);
	latestAgentAudio.set(null);
}

function mergeTranscriptText(previous: string, incoming: string): string {
	const prev = previous.trim();
	const next = incoming.trim();

	if (!prev) return next;
	if (!next) return prev;

	// If transport sends cumulative text, prefer the longer/latest cumulative value.
	if (next.startsWith(prev)) return next;
	if (prev.startsWith(next)) return prev;

	// If values only differ in whitespace around punctuation, keep the longer one.
	const normalize = (value: string): string =>
		value
			.replace(/\s+/g, " ")
			.replace(/\s+([.,!?;:])/g, "$1")
			.trim()
			.toLowerCase();
	const prevNormalized = normalize(prev);
	const nextNormalized = normalize(next);
	if (prevNormalized === nextNormalized) {
		return next.length >= prev.length ? next : prev;
	}

	// Character overlap merge to handle non-tokenized stream chunks.
	const maxOverlap = Math.min(prev.length, next.length);
	for (let overlap = maxOverlap; overlap > 0; overlap -= 1) {
		if (prev.slice(-overlap) === next.slice(0, overlap)) {
			return `${prev}${next.slice(overlap)}`.trim();
		}
	}

	// If transport sends token deltas, stitch naturally.
	if (/^[.,!?;:]$/.test(next)) {
		return `${prev}${next}`;
	}

	return `${prev} ${next}`;
}

function appendTranscript(event: TranscriptEvent): void {
	transcripts.update((items) => {
		const last = items[items.length - 1];

		if (last && last.role === event.role) {
			const mergedText = mergeTranscriptText(last.text, event.text);
			const merged = {
				...last,
				text: mergedText,
				isFinal: event.isFinal,
				ts: event.ts,
			};

			if (event.role === "user") {
				currentUserTranscript.set(mergedText);
			} else {
				currentAgentTranscript.set(mergedText);
			}

			return [...items.slice(0, -1), merged];
		}

		const transcript = {
			...event,
			id: `${event.role}-${event.ts}-${transcriptIdCounter++}`,
		};

		if (transcript.role === "user") {
			currentUserTranscript.set(transcript.text);
		} else {
			currentAgentTranscript.set(transcript.text);
		}

		return [...items, transcript];
	});
}

export async function startVoiceSession(contextId?: string): Promise<void> {
	if (isStarting) {
		throw new Error("A voice session is already starting");
	}

	isStarting = true;
	const startToken = ++startTokenCounter;
	const localClient = new VoiceClient();

	voiceError.set(null);
	transcripts.set([]);
	currentUserTranscript.set("");
	currentAgentTranscript.set("");
	resetVoiceCallState();

	// Clean up any existing client before creating a new one
	const existingClient = client;
	if (existingClient) {
		client = null;
		try {
			await existingClient.stopSession();
		} catch (err) {
			console.error("Error cleaning up existing client:", err);
		}
	}

	localClient.onTranscript = appendTranscript;
	localClient.onStateChange = (state) => {
		voiceState.set(state);
	};
	localClient.onAgentAudio = (audioData) => {
		latestAgentAudio.set(audioData);
	};
	localClient.onError = (message) => {
		voiceError.set(message);
		voiceState.set("error");
	};

	voiceState.set("connecting");
	try {
		const session = await localClient.startSession(contextId);
		if (startToken !== startTokenCounter) {
			await localClient.stopSession().catch(() => undefined);
			return;
		}
		voiceSessionId.set(session.session_id);
		voiceContextId.set(session.context_id);

		client = localClient;
		await localClient.connect(session.ws_url, session.session_id, session.session_token);
		if (startToken !== startTokenCounter) {
			await localClient.stopSession().catch(() => undefined);
			return;
		}
	} catch (err) {
		// On failure, clear the partially-initialized client
		if (client === localClient) {
			client = null;
		}
		const errorMessage = err instanceof Error ? err.message : String(err);
		voiceError.set(errorMessage);
		voiceState.set("error");
		await localClient.stopSession().catch(() => undefined);
		voiceSessionId.set(null);
		voiceContextId.set(null);
		throw err;
	} finally {
		if (startToken === startTokenCounter) {
			isStarting = false;
		}
	}
}

export async function endVoiceSession(): Promise<void> {
	startTokenCounter += 1;
	const active = client;
	client = null;

	if (active) {
		try {
			await active.stopSession();
		} catch (err) {
			console.error("Error stopping voice session:", err);
			// Continue with cleanup even if stopSession throws
		}
	}

	// Reset all state variables
	voiceSessionId.set(null);
	voiceContextId.set(null);
	resetVoiceCallState();
	voiceState.set("idle");
}

export function toggleMute(): void {
	if (!client) {
		return;
	}

	const muted = get(isVoiceMuted);
	if (muted) {
		client.unmute();
		isVoiceMuted.set(false);
	} else {
		client.mute();
		isVoiceMuted.set(true);
	}
}

export async function sendVoiceText(text: string): Promise<void> {
	if (!client) {
		throw new Error("No active voice session");
	}
	await client.sendUserText(text);
}

export function commitVoiceTurn(): void {
	if (!client) {
		return;
	}
	client.commitTurn();
}

export async function startVoiceStreaming(): Promise<void> {
	if (!client) {
		throw new Error("No active voice session");
	}
	await client.startAudioStreaming();
}

export function stopVoiceStreaming(): void {
	client?.stopAudioStreaming();
}

export function holdVoiceInputFor(ms: number): void {
	if (!client || ms <= 0) {
		return;
	}
	client.holdMicFor(ms);
}
