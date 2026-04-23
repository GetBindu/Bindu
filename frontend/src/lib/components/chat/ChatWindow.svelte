<script lang="ts">
	import type { Message, MessageFile } from "$lib/types/Message";
	import { onDestroy } from "svelte";

	import IconArrowUp from "~icons/lucide/arrow-up";
	import IconMic from "~icons/lucide/mic";

	import ChatInput from "./ChatInput.svelte";
	import VoiceRecorder from "./VoiceRecorder.svelte";
	import StopGeneratingBtn from "../StopGeneratingBtn.svelte";
	import type { Model } from "$lib/types/Model";
	import FileDropzone from "./FileDropzone.svelte";
	import RetryBtn from "../RetryBtn.svelte";
	import file2base64 from "$lib/utils/file2base64";
	import { base } from "$app/paths";
	import ChatMessage from "./ChatMessage.svelte";
	import ScrollToBottomBtn from "../ScrollToBottomBtn.svelte";
	import ScrollToPreviousBtn from "../ScrollToPreviousBtn.svelte";
	import { browser } from "$app/environment";
	import { snapScrollToBottom } from "$lib/actions/snapScrollToBottom";
	import SystemPromptModal from "../SystemPromptModal.svelte";
	import ShareConversationModal from "../ShareConversationModal.svelte";
	import ChatIntroduction from "./ChatIntroduction.svelte";
	import UploadedFile from "./UploadedFile.svelte";
	import { useSettingsStore } from "$lib/stores/settings";
	import { error } from "$lib/stores/errors";
	import { shareModal } from "$lib/stores/shareModal";
	import LucideHammer from "~icons/lucide/hammer";
	import ReplyIndicator from "./ReplyIndicator.svelte";
	import { agentInspector, resetAgentInspector } from "$lib/stores/agentInspector";

	import { fly } from "svelte/transition";
	import { cubicInOut } from "svelte/easing";

	import { isVirtualKeyboard } from "$lib/utils/isVirtualKeyboard";
	import { requireAuthUser } from "$lib/utils/auth";
	import { page } from "$app/state";
	import {
		isMessageToolCallUpdate,
		isMessageToolErrorUpdate,
		isMessageToolResultUpdate,
	} from "$lib/utils/messageUpdates";
	import type { ToolFront } from "$lib/types/Tool";

	interface Props {
		messages?: Message[];
		messagesAlternatives?: Message["id"][][];
		loading?: boolean;
		pending?: boolean;
		shared?: boolean;
		currentModel: Model;
		models: Model[];
		preprompt?: string | undefined;
		files?: File[];
		onmessage?: (content: string) => void;
		onstop?: () => void;
		onretry?: (payload: { id: Message["id"]; content?: string }) => void;
		onshowAlternateMsg?: (payload: { id: Message["id"] }) => void;
		onReplyToTask?: (taskId: string) => void;
		replyToTaskId?: string | null;
		onClearReply?: () => void;
		/** Optional override for what we show as "Session" identity */
		sessionId?: string | null;
		onClearContext?: () => void | Promise<void>;
		onClearTasks?: () => void | Promise<void>;
		draft?: string;
	}

	let {
		messages = [],
		messagesAlternatives = [],
		loading = false,
		pending = false,
		shared = false,
		currentModel,
		models,
		preprompt = undefined,
		files = $bindable([]),
		draft = $bindable(""),
		onmessage,
		onstop,
		onretry,
		onshowAlternateMsg,
		onReplyToTask,
		replyToTaskId = null,
		onClearReply,
		sessionId = null,
		onClearContext,
		onClearTasks,
	}: Props = $props();

	let isReadOnly = $derived(!models.some((model) => model.id === currentModel.id));

	let agentContextId = $derived.by(() => {
		// Derive from message task metadata when available (works for both normal and agent mode).
		for (let i = messages.length - 1; i >= 0; i -= 1) {
			const cid = messages[i]?.taskMetadata?.contextId;
			if (cid) return cid;
		}
		return null;
	});

	let agentTaskCount = $derived.by(() => {
		const ids = new Set<string>();
		for (const m of messages) {
			const tid = m.taskMetadata?.taskId;
			if (tid) ids.add(tid);
		}
		return ids.size;
	});

	let agentSessionId = $derived.by(() => {
		// Prefer an explicit session id, then the derived context id, then route param id if present.
		return sessionId ?? agentContextId ?? (page.params as Record<string, string> | undefined)?.id ?? null;
	});

	// Publish agent state + clear handlers for the sidebar inspector.
	$effect(() => {
		agentInspector.set({
			agentName: currentModel.displayName,
			contextId: agentContextId,
			sessionId: agentSessionId,
			taskCount: agentTaskCount,
			disabled: loading,
			onClearContext,
			onClearTasks,
		});
	});

	let shareModalOpen = $state(false);
	let editMsdgId: Message["id"] | null = $state(null);
	let pastedLongContent = $state(false);

	// Voice recording state
	let isRecording = $state(false);
	let isTranscribing = $state(false);
	let transcriptionEnabled = $derived(
		!!(page.data as { transcriptionEnabled?: boolean }).transcriptionEnabled
	);
	let isTouchDevice = $derived(browser && navigator.maxTouchPoints > 0);

	const handleSubmit = () => {
		if (requireAuthUser() || loading || !draft) return;
		onmessage?.(draft);
		draft = "";
	};

	let lastTarget: EventTarget | null = null;

	let onDrag = $state(false);

	const onDragEnter = (e: DragEvent) => {
		lastTarget = e.target;
		onDrag = true;
	};
	const onDragLeave = (e: DragEvent) => {
		if (e.target === lastTarget) {
			onDrag = false;
		}
	};

	const onPaste = (e: ClipboardEvent) => {
		const textContent = e.clipboardData?.getData("text");

		if (!$settings.directPaste && textContent && textContent.length >= 3984) {
			e.preventDefault();
			pastedLongContent = true;
			setTimeout(() => {
				pastedLongContent = false;
			}, 1000);
			const pastedFile = new File([textContent], "Pasted Content", {
				type: "application/vnd.bindu_ui.clipboard",
			});

			files = [...files, pastedFile];
		}

		if (!e.clipboardData) {
			return;
		}

		// paste of files
		const pastedFiles = Array.from(e.clipboardData.files);
		if (pastedFiles.length !== 0) {
			e.preventDefault();

			// filter based on activeMimeTypes, including wildcards
			const filteredFiles = pastedFiles.filter((file) => {
				return activeMimeTypes.some((mimeType: string) => {
					const [type, subtype] = mimeType.split("/");
					const [fileType, fileSubtype] = file.type.split("/");
					return (
						(type === "*" || fileType === type) && (subtype === "*" || fileSubtype === subtype)
					);
				});
			});

			files = [...files, ...filteredFiles];
		}
	};

	let lastMessage = $derived(browser && (messages.at(-1) as Message));
	// Scroll signal includes tool updates and thinking blocks to trigger scroll on all content changes
	let scrollSignal = $derived.by(() => {
		const last = messages.at(-1) as Message | undefined;
		if (!last) return `${messages.length}:0`;

		// Count tool updates to trigger scroll when new tools are called or complete
		const toolUpdateCount = last.updates?.length ?? 0;

		// Include content length, tool count, and message count in signal
		return `${last.id}:${last.content.length}:${messages.length}:${toolUpdateCount}`;
	});
	let streamingAssistantMessage = $derived(
		(() => {
			for (let i = messages.length - 1; i >= 0; i -= 1) {
				const candidate = messages[i];
				if (candidate.from === "assistant") {
					return candidate;
				}
			}
			return undefined;
		})()
	);

	let lastIsError = $derived(
		!loading &&
			(streamingAssistantMessage?.updates?.findIndex(
				(u) => u.type === "status" && u.status === "error"
			) ?? -1) !== -1
	);

	// Expose currently running tool call name (if any) from the streaming assistant message
	const availableTools: ToolFront[] = $derived.by(
		() => (page.data as { tools?: ToolFront[] } | undefined)?.tools ?? []
	);
	let streamingToolCallName = $derived.by(() => {
		const updates = streamingAssistantMessage?.updates ?? [];
		if (!updates.length) return null;
		const done = new Set<string>();
		for (const u of updates) {
			if (isMessageToolResultUpdate(u) || isMessageToolErrorUpdate(u)) done.add(u.uuid);
		}
		for (let i = updates.length - 1; i >= 0; i -= 1) {
			const u = updates[i];
			if (isMessageToolCallUpdate(u) && !done.has(u.uuid)) {
				return u.call.name;
			}
		}
		return null;
	});

	let sources = $derived(
		files?.map<Promise<MessageFile>>((file) =>
			file2base64(file).then((value) => ({
				type: "base64",
				value,
				mime: file.type,
				name: file.name,
			}))
		)
	);

	const unsubscribeShareModal = shareModal.subscribe((value) => {
		shareModalOpen = value;
	});

	onDestroy(() => {
		unsubscribeShareModal();
		shareModal.close();
		resetAgentInspector();
	});

	let chatContainer: HTMLElement | undefined = $state();

	// Force scroll to bottom when user sends a new message
	// Pattern: user message + empty assistant message are added together
	let prevMessageCount = $state(messages.length);
	let forceReattach = $state(0);
	$effect(() => {
		if (messages.length > prevMessageCount) {
			const last = messages.at(-1);
			const secondLast = messages.at(-2);
			const userJustSentMessage =
				messages.length === prevMessageCount + 2 &&
				secondLast?.from === "user" &&
				last?.from === "assistant" &&
				last?.content === "";

			if (userJustSentMessage) {
				forceReattach++;
			}
		}
		prevMessageCount = messages.length;
	});

	// Combined scroll dependency for the action
	let scrollDependency = $derived({ signal: scrollSignal, forceReattach });

	const settings = useSettingsStore();

	// Model capabilities - use model defaults
	let modelIsMultimodal = $derived(currentModel.multimodal === true);
	let modelSupportsTools = $derived(
		(currentModel as unknown as { supportsTools?: boolean }).supportsTools === true
	);

	// Always allow common text-like files; add images only when model is multimodal
	import { TEXT_MIME_ALLOWLIST, IMAGE_MIME_ALLOWLIST_DEFAULT, DOCUMENT_MIME_ALLOWLIST } from "$lib/constants/mime";

	let activeMimeTypes = $derived(
		Array.from(
			new Set([
				...TEXT_MIME_ALLOWLIST,
				...DOCUMENT_MIME_ALLOWLIST,
				...(modelIsMultimodal
					? (currentModel.multimodalAcceptedMimetypes ?? [...IMAGE_MIME_ALLOWLIST_DEFAULT])
					: []),
			])
		)
	);
	let isFileUploadEnabled = $derived(activeMimeTypes.length > 0);
	let focused = $state(false);


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
			const trimmedText = text?.trim();
			if (trimmedText) {
				// Append transcribed text to draft
				draft = draft.trim() ? `${draft.trim()} ${trimmedText}` : trimmedText;
			}
		} catch (err) {
			console.error("Transcription error:", err);
			$error = "Transcription failed. Please try again.";
		} finally {
			isTranscribing = false;
		}
	}

	async function handleRecordingSend(audioBlob: Blob) {
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
			const trimmedText = text?.trim();
			if (trimmedText) {
				// Set draft and send immediately
				draft = draft.trim() ? `${draft.trim()} ${trimmedText}` : trimmedText;
				handleSubmit();
			}
		} catch (err) {
			console.error("Transcription error:", err);
			$error = "Transcription failed. Please try again.";
		} finally {
			isTranscribing = false;
		}
	}

	function handleRecordingError(message: string) {
		console.error("Recording error:", message);
		isRecording = false;
		$error = message;
	}
</script>

<svelte:window
	ondragenter={onDragEnter}
	ondragleave={onDragLeave}
	ondragover={(e) => {
		e.preventDefault();
	}}
	ondrop={(e) => {
		e.preventDefault();
		onDrag = false;
	}}
/>

<div class="relative flex h-full min-h-0 min-w-0 flex-col">

	{#if shareModalOpen}
		<ShareConversationModal open={shareModalOpen} onclose={() => shareModal.close()} />
	{/if}
	<div
		class="scrollbar-custom flex-1 overflow-y-auto"
		use:snapScrollToBottom={scrollDependency}
		bind:this={chatContainer}
	>

		{#if replyToTaskId}
			<ReplyIndicator taskId={replyToTaskId} onClear={onClearReply ?? (() => {})} />
		{/if}
		<div
			class="mx-auto flex h-full max-w-3xl flex-col gap-6 px-5 pt-6 sm:gap-8 xl:max-w-4xl xl:pt-10"
		>
			{#if preprompt && preprompt != currentModel.preprompt}
				<SystemPromptModal preprompt={preprompt ?? ""} />
			{/if}

			{#if messages.length > 0}
				<div class="flex h-max flex-col gap-8 pb-40">
					{#each messages as message, idx (message.id)}
						<ChatMessage
							{loading}
							{message}
							alternatives={messagesAlternatives.find((a) => a.includes(message.id)) ?? []}
							isAuthor={!shared}
							readOnly={isReadOnly}
							isLast={idx === messages.length - 1}
							bind:editMsdgId
							onretry={(payload) => onretry?.(payload)}
							onshowAlternateMsg={(payload) => onshowAlternateMsg?.(payload)}
							onReplyToTask={onReplyToTask}
						/>
					{/each}
									</div>
			{:else if pending}
				<ChatMessage
					loading={true}
					message={{
						id: "0-0-0-0-0",
						content: "",
						from: "assistant",
						children: [],
					}}
					isAuthor={!shared}
					readOnly={isReadOnly}
				/>
			{:else}
				<div class="intro-container my-auto flex flex-1 flex-col items-center justify-center py-6 pb-52 sm:py-12 sm:pb-64">
					<ChatIntroduction
						{currentModel}
						onmessage={(content) => {
							onmessage?.(content);
						}}
					/>
					{#if !loading && !pending}
						<div
							class="intro-pills mt-10 flex flex-wrap items-center justify-center gap-2.5 px-4 transition-opacity duration-300"
							transition:fade
						>
							{#each [
								{ text: "Generate an image", icon: "🎨" },
								{ text: "Latest world news", icon: "📰" },
								{ text: "Trending models", icon: "🚀" },
								{ text: "Plan a trip", icon: "🗺️" },
								{ text: "Compare technologies", icon: "💻" },
								{ text: "Find a dataset", icon: "📊" },
								{ text: "Gift ideas", icon: "🎁" }
							] as prompt}
								<button
									type="button"
									class="prompt-pill flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-xs font-bold transition-all"
									onclick={() => {
										draft = prompt.text;
										handleSubmit();
									}}
								>
									{prompt.text}
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<ScrollToPreviousBtn class="fixed bottom-48 right-4 lg:right-10" scrollNode={chatContainer} />

		<ScrollToBottomBtn class="fixed bottom-36 right-4 lg:right-10" scrollNode={chatContainer} />
	</div>

	<div
		class="pointer-events-none absolute inset-x-0 bottom-0 z-0 mx-auto flex w-full
			max-w-3xl flex-col items-center justify-end bg-transparent
			px-3.5 pt-2 pb-6 sm:px-5 md:pb-8 xl:max-w-4xl [&>*]:pointer-events-auto"
	>

		{#if sources?.length && !loading}
			<div
				in:fly|local={sources.length === 1 ? { y: -20, easing: cubicInOut } : undefined}
				class="flex flex-row flex-wrap justify-center gap-2.5 rounded-xl pb-3"
			>
				{#each sources as source, index}
					{#await source then src}
						<UploadedFile
							file={src}
							onclose={() => {
								files = files.filter((_, i) => i !== index);
							}}
						/>
					{/await}
				{/each}
			</div>
		{/if}

		<div class="w-full">
			<!-- pills removed from here to prevent absolute overlap -->

			<div class="flex w-full *:mb-3">
				{#if !loading && lastIsError}
					<RetryBtn
						classNames="ml-auto"
						onClick={() => {
							if (lastMessage && lastMessage.ancestors) {
								onretry?.({
									id: lastMessage.id,
								});
							}
						}}
					/>
				{/if}
			</div>
		<!-- Chat composer wrapper with glow effects -->
		<div class="composer-wrap">
			<!-- Left orange glow -->
			<div class="composer-glow composer-glow-left"></div>
			<!-- Right blue glow -->
			<div class="composer-glow composer-glow-right"></div>

			<form
				tabindex="-1"
				aria-label={isFileUploadEnabled ? "file dropzone" : undefined}
				onsubmit={(e) => {
					e.preventDefault();
					handleSubmit();
				}}
				class="composer {isReadOnly ? 'opacity-30' : ''} {focused && isVirtualKeyboard() ? 'max-sm:mb-4' : ''} {pastedLongContent ? 'paste-glow' : ''}"
			>
				{#if isRecording || isTranscribing}
					<VoiceRecorder
						{isTranscribing}
						{isTouchDevice}
						oncancel={() => {
							isRecording = false;
						}}
						onconfirm={handleRecordingConfirm}
						onsend={handleRecordingSend}
						onerror={handleRecordingError}
					/>
				{:else if onDrag && isFileUploadEnabled}
					<FileDropzone bind:files bind:onDrag mimeTypes={activeMimeTypes} />
				{:else}
					{#if lastIsError}
						<ChatInput value="Sorry, something went wrong. Please try again." disabled={true} />
					{:else}
						<ChatInput
							placeholder={isReadOnly ? "This conversation is read-only." : "Ask anything"}
							{loading}
							bind:value={draft}
							bind:files
							mimeTypes={activeMimeTypes}
							onsubmit={handleSubmit}
							{onPaste}
							disabled={isReadOnly || lastIsError}
							{modelIsMultimodal}
							{modelSupportsTools}
							bind:focused
						>
							{#if loading}
								<StopGeneratingBtn
									onClick={() => onstop?.()}
									showBorder={true}
									classNames="composer-btn icon-btn"
								/>
							{:else}
								{#if transcriptionEnabled}
									<button
										type="button"
										class="composer-btn"
										disabled={isReadOnly}
										onclick={() => {
											isRecording = true;
										}}
										aria-label="Start voice recording"
									>
										<IconMic class="size-3.5" />
										<span>Voice</span>
									</button>
								{/if}
								<button
									class="send-btn"
									disabled={!draft || isReadOnly}
									type="submit"
									aria-label="Send message"
									name="submit"
								>
									<IconArrowUp class="size-4" />
								</button>
							{/if}
						</ChatInput>
					{/if}
				{/if}
			</form>
		</div>
			<div class="mt-2 flex h-5 items-center justify-center self-stretch whitespace-nowrap px-0.5 text-[10px] text-gray-450 dark:text-gray-500 max-md:mb-2 {focused && isVirtualKeyboard() ? 'max-sm:hidden' : ''}">
				{#if loading && streamingToolCallName}
					<span class="inline-flex items-center gap-1 whitespace-nowrap">
						<LucideHammer class="size-3" />
						Calling tool
						<span class="loading-dots font-medium">
							{availableTools.find((t) => t.name === streamingToolCallName)?.displayName ??
								streamingToolCallName}
						</span>
					</span>
				{:else}
					<div class="flex items-center gap-1.5 uppercase tracking-wider">
						<span>{currentModel.displayName}</span>
						{#if !messages.length && !loading}
							<span class="mx-1 opacity-50">•</span>
							<span>Generated content may be inaccurate or false.</span>
						{/if}
					</div>
				{/if}
			</div>
		</div>

	</div>
</div>

<style lang="postcss">
	@media (max-height: 580px) {
		.intro-pills {
			display: none !important;
		}
		.intro-container {
			padding-top: 1rem !important;
			padding-bottom: 1rem !important;
			margin-top: 2rem !important;
		}
	}

	/* Wrapper */
	.composer-wrap {
		position: relative;
		width: min(760px, 92vw);
		margin: 0 auto;
		padding: 80px 0 60px;
		display: flex;
		justify-content: center;
		align-items: center;
		isolation: isolate;
	}

	/* Glow Layers */
	.composer-glow {
		position: absolute;
		inset: -120px;
		z-index: 0;
		pointer-events: none;
		filter: blur(90px);
		opacity: 0.95;
		transition: opacity 0.3s ease;
	}

	:global(html:not(.dark)) .composer-glow {
		opacity: 0.25;
		filter: blur(120px);
	}

	/* TOP-LEFT — ORANGE */
	.composer-glow-left {
		background:
			radial-gradient(circle at 16% 45%,
				rgba(255, 110, 60, 0.95) 0%,
				rgba(255, 110, 60, 0.4) 12%,
				rgba(255, 110, 60, 0.1) 25%,
				transparent 45%);
	}

	/* BOTTOM-RIGHT — BLUE */
	.composer-glow-right {
		background:
			radial-gradient(circle at 84% 55%,
				rgba(90, 140, 255, 0.95) 0%,
				rgba(90, 140, 255, 0.4) 12%,
				rgba(96, 92, 255, 0.1) 25%,
				transparent 45%);
	}

	/* Glass Core */
	.composer {
		position: relative;
		z-index: 2;
		width: 100%;
		height: 84px;
		border-radius: 22px;
		background: rgba(8, 9, 14, 0.97);
		border: 1px solid rgba(255, 255, 255, 0.06);
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		box-shadow:
			inset 0 1px 0 rgba(255, 255, 255, 0.03),
			0 20px 60px rgba(0, 0, 0, 0.8);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		justify-content: center;
		padding: 10px 14px;
		gap: 6px;
	}

	:global(html:not(.dark)) .composer {
		background: #ffffff;
		border-color: rgba(15, 23, 42, 0.08);
		box-shadow:
			0 1px 2px rgba(15, 23, 42, 0.05),
			0 12px 24px -4px rgba(15, 23, 42, 0.04),
			0 20px 48px -8px rgba(15, 23, 42, 0.1);
	}

	/* Gradient Rim */
	.composer::before {
		content: "";
		position: absolute;
		inset: 0;
		border-radius: inherit;
		padding: 1px;
		background: linear-gradient(
			135deg,
			rgba(255, 110, 60, 0.8) 0%,
			rgba(255, 255, 255, 0.02) 40%,
			rgba(255, 255, 255, 0.02) 60%,
			rgba(90, 140, 255, 0.8) 100%
		);
		-webkit-mask:
			linear-gradient(#fff 0 0) content-box,
			linear-gradient(#fff 0 0);
		-webkit-mask-composite: xor;
		        mask-composite: exclude;
		pointer-events: none;
	}

	:global(html:not(.dark)) .composer::before {
		background: linear-gradient(
			135deg,
			rgba(99, 102, 241, 0.2) 0%,
			rgba(15, 23, 42, 0.02) 40%,
			rgba(15, 23, 42, 0.02) 60%,
			rgba(236, 72, 153, 0.2) 100%
		);
	}

	/* Font Fixes */
	.composer :global(textarea),
	.composer :global(input[type="text"]) {
		font-family: Inter, system-ui, -apple-system, sans-serif !important;
		color: #111827;
		font-size: 15px;
		line-height: 1.5;
	}

	:global(.dark) .composer :global(textarea),
	:global(.dark) .composer :global(input[type="text"]) {
		color: #eef1f7;
	}

	.composer :global(textarea::placeholder) {
		color: rgba(71, 85, 105, 0.6);
	}

	:global(.dark) .composer :global(textarea::placeholder) {
		color: rgba(168, 177, 197, 0.62);
	}



	/* Pill Buttons */
	:global(.composer-btn) {
		height: 28px;
		padding: 0 12px;
		border-radius: 999px;
		background: rgba(0, 0, 0, 0.04);
		border: 1px solid rgba(0, 0, 0, 0.08);
		color: rgba(51, 65, 85, 0.8);
		font-family: Inter, system-ui, sans-serif;
		font-size: 12.5px;
		line-height: 1;
		display: inline-flex;
		align-items: center;
		gap: 5px;
		cursor: pointer;
		white-space: nowrap;
		outline: none;
		transition: background 0.15s, color 0.15s;
		flex-shrink: 0;
	}

	:global(.dark) :global(.composer-btn) {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: rgba(210, 218, 235, 0.75);
	}

	:global(.composer-btn:hover:not(:disabled)) {
		background: rgba(0, 0, 0, 0.08);
		color: rgba(15, 23, 42, 0.95);
	}

	:global(.dark) :global(.composer-btn:hover:not(:disabled)) {
		background: rgba(255, 255, 255, 0.07);
		color: rgba(225, 232, 248, 0.95);
	}

	:global(.composer-btn:disabled) {
		opacity: 0.45;
		cursor: not-allowed;
	}

	/* Icon-only pill (+ button) */
	:global(.icon-btn) {
		width: 28px;
		height: 28px;
		padding: 0;
		display: grid;
		place-items: center;
	}

	/* Send Button */
	.send-btn {
		width: 32px;
		height: 32px;
		flex-shrink: 0;
		border: none;
		border-radius: 50%;
		color: #fff;
		background: linear-gradient(135deg, #8c4cff, #ff4fd8);
		box-shadow:
			0 0 12px rgba(140, 76, 255, 0.6),
			0 0 22px rgba(255, 79, 216, 0.4);
		display: grid;
		place-items: center;
		cursor: pointer;
		outline: none;
		transition: transform 0.15s, box-shadow 0.15s;
	}

	.send-btn:disabled {
		opacity: 0.45;
		box-shadow: none;
		cursor: not-allowed;
	}

	.send-btn:not(:disabled):hover {
		transform: scale(1.08);
		box-shadow:
			0 0 16px rgba(140, 76, 255, 0.8),
			0 0 28px rgba(255, 79, 216, 0.55);
	}

	/* Paste Glow Animation */
	.paste-glow {
		animation: paste-pulse 1s cubic-bezier(0.4, 0, 0.2, 1) forwards;
	}

	@keyframes paste-pulse {
		0%   { box-shadow: 0 0 0 0 rgba(140, 76, 255, 0.8); }
		50%  { box-shadow: 0 0 20px 4px rgba(140, 76, 255, 0.6); }
		100% { box-shadow: 0 0 0 0 rgba(140, 76, 255, 0); }
	}

	/* Prompt Pills (suggestions) */
	.prompt-pill {
		background: var(--pill-bg);
		border: 1px solid var(--pill-border);
		color: #475569;
		font-family: Inter, system-ui, sans-serif;
		font-size: 12px;
		transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
		box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
	}

	:global(.dark) .prompt-pill {
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.08);
		color: rgba(210, 218, 235, 0.7);
		box-shadow: none;
	}

	.prompt-pill:hover {
		background: #ffffff;
		color: #0f172a;
		border-color: #cbd5e1;
		transform: translateY(-1px);
		box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.1);
	}

	:global(.dark) .prompt-pill:hover {
		background: rgba(255, 255, 255, 0.07);
		color: rgba(225, 232, 248, 0.9);
		border-color: rgba(255, 255, 255, 0.15);
		transform: none;
		box-shadow: none;
	}

	/* Loading Dots */
	.loading-dots::after {
		content: "";
		animation: dots-content 0.9s steps(1, end) infinite;
	}

	@keyframes dots-content {
		0%  { content: ""; }
		33% { content: "."; }
		66% { content: ".."; }
		88% { content: "..."; }
	}
</style>
