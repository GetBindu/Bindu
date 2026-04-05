import { get, writable } from 'svelte/store';
import { VoiceClient, type TranscriptEvent, type VoiceState } from '../services/voice-client';

export type VoiceTranscript = TranscriptEvent & { id: string };

export const voiceSessionId = writable<string | null>(null);
export const voiceContextId = writable<string | null>(null);
export const voiceState = writable<VoiceState>('idle');
export const isVoiceMuted = writable<boolean>(false);
export const transcripts = writable<VoiceTranscript[]>([]);
export const currentUserTranscript = writable<string>('');
export const currentAgentTranscript = writable<string>('');
export const latestAgentAudio = writable<ArrayBuffer | null>(null);
export const voiceError = writable<string | null>(null);

let client: VoiceClient | null = null;
let isStarting = false;
let startTokenCounter = 0;
let transcriptIdCounter = 0;

function appendTranscript(event: TranscriptEvent): void {
  const transcript = {
    ...event,
    id: `${event.role}-${event.ts}-${transcriptIdCounter++}`,
  };
  transcripts.update((items) => [...items, transcript]);
  if (transcript.role === 'user') {
    currentUserTranscript.set(transcript.text);
  } else {
    currentAgentTranscript.set(transcript.text);
  }
}

export async function startVoiceSession(contextId?: string): Promise<void> {
  if (isStarting) {
    throw new Error('A voice session is already starting');
  }

  isStarting = true;
  const startToken = ++startTokenCounter;
  const localClient = new VoiceClient();

  voiceError.set(null);
  transcripts.set([]);
  currentUserTranscript.set('');
  currentAgentTranscript.set('');

  // Clean up any existing client before creating a new one
  const existingClient = client;
  if (existingClient) {
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
    voiceState.set('error');
  };

  voiceState.set('connecting');
  try {
    const session = await localClient.startSession(contextId);
    if (startToken !== startTokenCounter) {
      await localClient.stopSession().catch(() => undefined);
      return;
    }
    voiceSessionId.set(session.session_id);
    voiceContextId.set(session.context_id);

    await localClient.connect(session.ws_url, session.session_id, session.session_token);
    if (startToken !== startTokenCounter) {
      await localClient.stopSession().catch(() => undefined);
      return;
    }
    client = localClient;
  } catch (err) {
    // On failure, clear the partially-initialized client
    const errorMessage = err instanceof Error ? err.message : String(err);
    voiceError.set(errorMessage);
    voiceState.set('error');
    if (client === localClient) {
      client = null;
    }
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
  isVoiceMuted.set(false);
  latestAgentAudio.set(null);
  voiceState.set('idle');
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
    throw new Error('No active voice session');
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
    throw new Error('No active voice session');
  }
  await client.startAudioStreaming();
}

export function stopVoiceStreaming(): void {
  client?.stopAudioStreaming();
}
