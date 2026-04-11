<script lang="ts">
	import LiveTranscript from "$lib/components/voice/LiveTranscript.svelte";
	import {
		endVoiceSession,
		holdVoiceInputFor,
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
	let playbackContext: AudioContext | null = $state(null);
	let playbackNextTime = $state(0);
	let lastAgentAudioAt = $state(0);
	let lastFallbackSpoken = $state("");
	let fallbackSpeechTimer: ReturnType<typeof setTimeout> | null = $state(null);

	function ensurePlaybackContext(sampleRate = 16000): AudioContext {
		if (playbackContext) {
			return playbackContext;
		}

		const AudioContextCtor =
			window.AudioContext ||
			(window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

		if (!AudioContextCtor) {
			throw new Error("AudioContext is not supported in this browser");
		}

		playbackContext = new AudioContextCtor({ sampleRate });
		playbackNextTime = 0;
		return playbackContext;
	}

	function pcm16ToFloat32(pcmBuffer: ArrayBuffer): Float32Array {
		const pcm = new Int16Array(pcmBuffer);
		const out = new Float32Array(pcm.length);
		for (let i = 0; i < pcm.length; i++) {
			out[i] = (pcm[i] ?? 0) / 32768;
		}
		return out;
	}

	async function queueAgentAudio(pcmBuffer: ArrayBuffer, sampleRate = 16000): Promise<void> {
		const ctx = ensurePlaybackContext(sampleRate);
		if (ctx.state === "suspended") {
			await ctx.resume();
		}

		const samples = pcm16ToFloat32(pcmBuffer);
		if (!samples.length) {
			return;
		}

		const audioBuffer = ctx.createBuffer(1, samples.length, sampleRate);
		const channelData = new Float32Array(samples);
		audioBuffer.copyToChannel(channelData, 0);

		const source = ctx.createBufferSource();
		source.buffer = audioBuffer;
		source.connect(ctx.destination);

		const startAt = Math.max(ctx.currentTime, playbackNextTime);
		source.start(startAt);
		playbackNextTime = startAt + audioBuffer.duration;

		// Keep scheduling stable if there's a long pause between chunks.
		if (playbackNextTime - ctx.currentTime > 2) {
			playbackNextTime = ctx.currentTime;
		}
	}

	$effect(() => {
		if (!$latestAgentAudio || $latestAgentAudio === lastAudioChunk) {
			return;
		}

		lastAudioChunk = $latestAgentAudio;
		lastAgentAudioAt = Date.now();
		void queueAgentAudio($latestAgentAudio).catch(() => {
			voiceError.set("Unable to play agent audio response");
		});
	});

	$effect(() => {
		const items = $transcripts;
		if (!items.length || $isVoiceMuted) {
			return;
		}

		const last = items[items.length - 1];
		if (!last || last.role !== "agent" || !last.isFinal) {
			return;
		}

		const text = last.text.trim();
		if (!text || text === lastFallbackSpoken) {
			return;
		}

		if (fallbackSpeechTimer) {
			clearTimeout(fallbackSpeechTimer);
		}

		fallbackSpeechTimer = setTimeout(() => {
			const elapsed = Date.now() - lastAgentAudioAt;
			if (elapsed < 1200) {
				return;
			}

			if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
				return;
			}

			const estimatedMs = Math.max(2500, Math.min(12000, text.length * 65));
			holdVoiceInputFor(estimatedMs + 1500);

			const utterance = new SpeechSynthesisUtterance(text);
			utterance.rate = 1;
			utterance.pitch = 1;
			utterance.volume = 1;
			window.speechSynthesis.cancel();
			window.speechSynthesis.speak(utterance);
			lastFallbackSpoken = text;
		}, 1300);

		return () => {
			if (fallbackSpeechTimer) {
				clearTimeout(fallbackSpeechTimer);
				fallbackSpeechTimer = null;
			}
		};
	});

	$effect(() => {
		if (!["idle", "ended", "error"].includes($voiceState)) {
			return;
		}

		playbackNextTime = 0;
		if (playbackContext) {
			void playbackContext.close();
			playbackContext = null;
		}

		if (fallbackSpeechTimer) {
			clearTimeout(fallbackSpeechTimer);
			fallbackSpeechTimer = null;
		}
		if ("speechSynthesis" in window) {
			window.speechSynthesis.cancel();
		}
		lastFallbackSpoken = "";
	});

	$effect(() => {
		if (["idle", "ended", "error"].includes($voiceState)) {
			isRecording = false;
		}
		if ($voiceState === "active" && !isRecording && !isStarting) {
			beginStreaming();
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

<div
	class="fixed inset-x-0 bottom-0 z-20 mx-auto mb-2 w-[min(52rem,95vw)] rounded-xl border border-gray-200 bg-white/95 p-3 shadow-2xl dark:border-gray-700 dark:bg-gray-900/95"
>
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
		<p
			class="mb-2 rounded-md bg-red-50 px-2 py-1 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300"
		>
			{$voiceError}
		</p>
	{/if}

	<LiveTranscript items={$transcripts} />
</div>
