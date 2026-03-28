<script lang="ts">
	import { base } from "$app/paths";
	import VoiceRecorder from "$lib/components/chat/VoiceRecorder.svelte";
	import LiveTranscript from "$lib/components/voice/LiveTranscript.svelte";
	import {
		endVoiceSession,
		isVoiceMuted,
		latestAgentAudio,
		sendVoiceText,
		toggleMute,
		transcripts,
		voiceError,
		voiceState,
	} from "$lib/stores/voice";
	import IconMic from "~icons/lucide/mic";
	import IconMicOff from "~icons/lucide/mic-off";
	import IconPhoneOff from "~icons/lucide/phone-off";

	let isRecording = $state(false);
	let isTranscribing = $state(false);
	let lastAudioChunk: ArrayBuffer | null = $state(null);

	$effect(() => {
		if (!$latestAgentAudio || $latestAgentAudio === lastAudioChunk) {
			return;
		}

		lastAudioChunk = $latestAgentAudio;
		const blob = new Blob([$latestAgentAudio], { type: "audio/mpeg" });
		const url = URL.createObjectURL(blob);
		const audio = new Audio(url);

		// Handle errors during playback
		const handleError = () => {
			URL.revokeObjectURL(url);
		};

		audio.onerror = handleError;

		// Start playback and handle failure
		audio.play().catch(() => {
			handleError();
		});

		// Cleanup function for when effect re-runs or component unmounts
		return () => {
			if (!audio.paused) {
				audio.pause();
			}
			audio.onended = null;
			audio.onerror = null;
			URL.revokeObjectURL(url);
		};
	});

	async function handleRecordingConfirm(audioBlob: Blob) {
		isRecording = false;
		isTranscribing = true;

		try {
			const response = await fetch(`${base}/api/transcribe`, {
				method: "POST",
				headers: { "Content-Type": audioBlob.type },
				body: audioBlob,
			});

			if (!response.ok) {
				throw new Error(await response.text());
			}

			const { text } = await response.json();
			if (text?.trim()) {
				await sendVoiceText(text.trim());
			}
		} catch (err) {
			voiceError.set((err as Error).message || "Transcription failed");
		} finally {
			isTranscribing = false;
		}
	}

</script>

<div class="fixed inset-x-0 bottom-0 z-20 mx-auto mb-2 w-[min(52rem,95vw)] rounded-xl border border-gray-200 bg-white/95 p-3 shadow-2xl dark:border-gray-700 dark:bg-gray-900/95">
	<div class="mb-2 flex items-center justify-between">
		<div>
			<div class="text-sm font-semibold">Voice Session</div>
			<div class="text-xs text-gray-500">State: {$voiceState}</div>
		</div>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="btn grid size-8 place-items-center rounded-full border bg-white text-black shadow transition-none hover:bg-gray-100 dark:border-transparent dark:bg-gray-600 dark:text-white dark:hover:bg-gray-500"
				onclick={() => toggleMute()}
				aria-label={$isVoiceMuted ? "Unmute" : "Mute"}
			>
				{#if $isVoiceMuted}
					<IconMicOff class="size-4" />
				{:else}
					<IconMic class="size-4" />
				{/if}
			</button>
			<button
				type="button"
				class="btn grid size-8 place-items-center rounded-full border border-transparent bg-red-600 text-white shadow transition-none hover:bg-red-500"
				onclick={() => endVoiceSession()}
				aria-label="End voice session"
			>
				<IconPhoneOff class="size-4" />
			</button>
		</div>
	</div>

	{#if $voiceError}
		<p class="mb-2 rounded-md bg-red-50 px-2 py-1 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">{$voiceError}</p>
	{/if}

	<LiveTranscript items={$transcripts} />

	<div class="mt-3">
		{#if isRecording || isTranscribing}
			<div class="rounded-xl border bg-gray-100 dark:border-gray-700 dark:bg-gray-800">
				<VoiceRecorder
					{isTranscribing}
					isTouchDevice={false}
					oncancel={() => {
						isRecording = false;
					}}
					onconfirm={handleRecordingConfirm}
					onsend={handleRecordingConfirm}
					onerror={(message) => {
						voiceError.set(message);
						isRecording = false;
					}}
				/>
			</div>
		{:else}
			<button
				type="button"
				class="btn rounded-lg border bg-white px-3 py-1.5 text-sm shadow transition-none hover:bg-gray-100 dark:border-transparent dark:bg-gray-600 dark:text-white dark:hover:bg-gray-500"
				onclick={() => {
					isRecording = true;
				}}
			>
				Tap to Speak
			</button>
		{/if}
	</div>
</div>
