import { get, writable } from 'svelte/store';
import { VoiceClient, type TranscriptEvent, type VoiceState } from '../services/voice-client';

export type VoiceTranscript = TranscriptEvent;

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

function appendTranscript(event: VoiceTranscript): void {
  transcripts.update((items) => [...items, event]);
  if (event.role === 'user') {
    currentUserTranscript.set(event.text);
  } else {
    currentAgentTranscript.set(event.text);
  }
}

export async function startVoiceSession(contextId?: string): Promise<void> {
  voiceError.set(null);
  transcripts.set([]);
  currentUserTranscript.set('');
  currentAgentTranscript.set('');

  client = new VoiceClient();
  client.onTranscript = appendTranscript;
  client.onStateChange = (state) => {
    voiceState.set(state);
  };
  client.onAgentAudio = (audioData) => {
    latestAgentAudio.set(audioData);
  };
  client.onError = (message) => {
    voiceError.set(message);
    voiceState.set('error');
  };

  voiceState.set('connecting');
  const session = await client.startSession(contextId);
  voiceSessionId.set(session.session_id);
  voiceContextId.set(session.context_id);

  await client.connect(session.ws_url, session.session_id);
}

export async function endVoiceSession(): Promise<void> {
  const active = client;
  client = null;

  if (active) {
    await active.stopSession();
  }

  voiceSessionId.set(null);
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
