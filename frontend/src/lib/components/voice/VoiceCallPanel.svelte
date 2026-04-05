<script lang="ts">
	import LiveTranscript from "$lib/components/voice/LiveTranscript.svelte";
	import {
		endVoiceSession,
		isVoiceMuted,
		latestAgentAudio,
		startVoiceStreaming,
		stopVoiceStreaming,
		toggleMute,
		transcripts,
		voiceError,
		voiceState,
	} from "$lib/stores/voice";
	import IconMic from "~icons/lucide/mic";
	import IconMicOff from "~icons/lucide/mic-off";
	import IconPhoneOff from "~icons/lucide/phone-off";

	let isRecording = $state(false);
	let isStarting = $state(false);
	let lastAudioChunk: ArrayBuffer | null = $state(null);

	function pcm16ToWavBuffer(
		pcmBuffer: ArrayBuffer,
		sampleRate = 16000,
		channels = 1
	): ArrayBuffer {
		const bytesPerSample = 2;
		const dataSize = pcmBuffer.byteLength;
		const blockAlign = channels * bytesPerSample;
		const byteRate = sampleRate * blockAlign;
		const wavBuffer = new ArrayBuffer(44 + dataSize);
		const view = new DataView(wavBuffer);

		const writeString = (offset: number, value: string) => {
			for (let i = 0; i < value.length; i++) {
				view.setUint8(offset + i, value.charCodeAt(i));
			}
		};

		writeString(0, "RIFF");
		view.setUint32(4, 36 + dataSize, true);
		writeString(8, "WAVE");
		writeString(12, "fmt ");
		view.setUint32(16, 16, true);
		view.setUint16(20, 1, true);
		view.setUint16(22, channels, true);
		view.setUint32(24, sampleRate, true);
		view.setUint32(28, byteRate, true);
		view.setUint16(32, blockAlign, true);
		view.setUint16(34, 16, true);
		writeString(36, "data");
		view.setUint32(40, dataSize, true);
		new Uint8Array(wavBuffer, 44).set(new Uint8Array(pcmBuffer));

		return wavBuffer;
	}

	$effect(() => {
		if (!$latestAgentAudio || $latestAgentAudio === lastAudioChunk) {
			return;
		}

		lastAudioChunk = $latestAgentAudio;
		const wavBuffer = pcm16ToWavBuffer($latestAgentAudio);
		const blob = new Blob([wavBuffer], { type: "audio/wav" });
		const url = URL.createObjectURL(blob);
		const audio = new Audio(url);

		const cleanup = () => {
			audio.onended = null;
			audio.onerror = null;
			URL.revokeObjectURL(url);
		};

		const handleError = () => {
			voiceError.set("Unable to play agent audio response");
			cleanup();
		};

		audio.onended = cleanup;
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
			cleanup();
		};
	});

	$effect(() => {
		if (["idle", "ended", "error"].includes($voiceState)) {
			isRecording = false;
		}
	});

	async function beginStreaming() {
		if (isStarting || isRecording) {
			return;
		}
		isStarting = true;
		isRecording = true;
		try {
			await startVoiceStreaming();
		} catch (err) {
			voiceError.set((err as Error).message || "Microphone access failed");
			isRecording = false;
		} finally {
			isStarting = false;
		}
	}

	function stopStreaming() {
		stopVoiceStreaming();
		isRecording = false;
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
		{#if isRecording}
			<button
				type="button"
				class="btn rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 shadow transition-none hover:bg-red-100 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200 dark:hover:bg-red-950/60"
				onclick={stopStreaming}
			>
				Stop Microphone
			</button>
			{:else}
				<button
					type="button"
					class="btn rounded-lg border bg-white px-3 py-1.5 text-sm shadow transition-none hover:bg-gray-100 dark:border-transparent dark:bg-gray-600 dark:text-white dark:hover:bg-gray-500"
					onclick={beginStreaming}
					disabled={isStarting}
				>
					{isStarting ? "Starting..." : "Start Microphone"}
				</button>
			{/if}
		</div>
	</div>
