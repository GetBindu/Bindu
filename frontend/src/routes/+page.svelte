<script lang="ts">
	import { goto, replaceState } from "$app/navigation";
	import { base } from "$app/paths";
	import { page } from "$app/state";
	import { usePublicConfig } from "$lib/utils/PublicConfig.svelte";

	const publicConfig = usePublicConfig();

	import ChatWindow from "$lib/components/chat/ChatWindow.svelte";
	import { ERROR_MESSAGES, error } from "$lib/stores/errors";
	import { pendingMessage } from "$lib/stores/pendingMessage";
	import { sanitizeUrlParam } from "$lib/utils/urlParams";
	import { onMount, tick } from "svelte";
	import { loading } from "$lib/stores/loading.js";
	import { loadAttachmentsFromUrls } from "$lib/utils/loadAttachmentsFromUrls";
	import { requireAuthUser } from "$lib/utils/auth";
	import {
		messages as agentMessages,
		isThinking,
		sendMessage as sendAgentMessage,
		contextId,
		currentTaskId,
		currentTaskState,
		createNewContext,
		clearContext as clearAgentContext,
		setReplyTo,
		clearReplyTo,
		replyToTaskId
	} from "$lib/stores/chat";
	import type { Message } from "$lib/types/Message";

	let { data } = $props();

	let hasModels = $derived(Boolean(data.models?.length));
	let files: File[] = $state([]);
	let draft = $state("");

	// Check if we're in agent mode (have an active context OR messages)
	// Keep agent mode active if we have messages, even if context temporarily clears
	let isAgentMode = $derived($contextId !== null || $agentMessages.length > 0);

	// Convert agent messages to display format
	let displayMessages = $derived($agentMessages.map(msg => ({
		id: msg.id,
		content: msg.text,
		from: (msg.role === 'user' ? 'user' : msg.role === 'assistant' ? 'assistant' : 'system') as 'user' | 'assistant' | 'system',
		children: [] as string[],
		createdAt: new Date(msg.timestamp),
		updatedAt: new Date(msg.timestamp),
		// Add taskMetadata so TaskInfo component can display info button
		...(msg.taskId && {
			taskMetadata: {
				taskId: msg.taskId,
				contextId: $contextId || undefined,
				status: msg.state || 'completed'
			}
		})
	} as Message)));

	// Debug logging
	$effect(() => {
		console.log('=== HOME PAGE STATE ===');
		console.log('isAgentMode:', isAgentMode);
		console.log('contextId:', $contextId);
		console.log('agentMessages count:', $agentMessages.length);
		console.log('displayMessages count:', displayMessages.length);
		console.log('isThinking:', $isThinking);
		console.log('Messages:', $agentMessages.map(m => ({ role: m.role, text: m.text.substring(0, 30) })));
		console.log('======================');
	});

	async function createConversation(message: string) {
		try {
			$loading = true;

			// Use the default (and only) model
			const model = data.models[0].id;

			const res = await fetch(`${base}/conversation`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					model,
				}),
			});

			if (!res.ok) {
				let errorMessage = ERROR_MESSAGES.default;
				try {
					const json = await res.json();
					errorMessage = json.message || errorMessage;
				} catch {
					// Response wasn't JSON (e.g., HTML error page)
					if (res.status === 401) {
						errorMessage = "Authentication required";
					}
				}
				error.set(errorMessage);
				console.error("Error while creating conversation: ", errorMessage);
				return;
			}

			const { conversationId } = await res.json();

			// Ugly hack to use a store as temp storage, feel free to improve ^^
			pendingMessage.set({
				content: message,
				files,
			});

			// invalidateAll to update list of conversations
			await goto(`${base}/conversation/${conversationId}`, { invalidateAll: true });
		} catch (err) {
			error.set((err as Error).message || ERROR_MESSAGES.default);
			console.error(err);
		} finally {
			$loading = false;
		}
	}

	onMount(async () => {
		try {
			// Check if auth is required before processing any query params
			const hasQ = page.url.searchParams.has("q");
			const hasPrompt = page.url.searchParams.has("prompt");
			const hasAttachments = page.url.searchParams.has("attachments");

			if ((hasQ || hasPrompt || hasAttachments) && requireAuthUser()) {
				return; // Redirecting to login, will return to this URL after
			}

			// Handle attachments parameter first
			if (hasAttachments) {
				const result = await loadAttachmentsFromUrls(page.url.searchParams);
				files = result.files;

				// Show errors if any
				if (result.errors.length > 0) {
					console.error("Failed to load some attachments:", result.errors);
					error.set(
						`Failed to load ${result.errors.length} attachment(s). Check console for details.`
					);
				}

				// Clean up URL
				const url = new URL(page.url);
				url.searchParams.delete("attachments");
				history.replaceState({}, "", url);
			}

			const query = sanitizeUrlParam(page.url.searchParams.get("q"));
			if (query) {
				void createConversation(query);
				const url = new URL(page.url);
				url.searchParams.delete("q");
				tick().then(() => {
					replaceState(url, page.state);
				});
				return;
			}

			const promptQuery = sanitizeUrlParam(page.url.searchParams.get("prompt"));
			if (promptQuery && !draft) {
				draft = promptQuery;
				const url = new URL(page.url);
				url.searchParams.delete("prompt");
				tick().then(() => {
					replaceState(url, page.state);
				});
			}
		} catch (err) {
			console.error("Failed to process URL parameters:", err);
		}
	});

	let currentModel = $derived(data.models[0]);

	async function handleMessage(message: string) {
		if (isAgentMode) {
			await sendAgentMessage(message);
		} else {
			await createConversation(message);
		}
	}

	function handleReplyToTask(taskId: string) {
		setReplyTo(taskId);
	}

	function handleClearReply() {
		clearReplyTo();
	}

	async function handleClearTasks() {
		// UI-only reset: start a fresh task thread (keep context if it exists)
		currentTaskId.set(null);
		currentTaskState.set(null);
		setReplyTo(null);
	}

	async function handleClearContext() {
		// Best-effort: reset UI immediately, then try clearing server-side if reachable.
		const ctx = $contextId;
		createNewContext();
		if (ctx) {
			await clearAgentContext(ctx);
		}
	}
</script>

<svelte:head>
	<title>{publicConfig.PUBLIC_APP_NAME}</title>
</svelte:head>

{#if hasModels}
	{#if isAgentMode}
		<ChatWindow
			messages={displayMessages}
			loading={$isThinking}
			{currentModel}
			models={data.models}
			onmessage={handleMessage}
			onReplyToTask={handleReplyToTask}
			replyToTaskId={$replyToTaskId}
			onClearReply={handleClearReply}
			onClearContext={handleClearContext}
			onClearTasks={handleClearTasks}
		/>
	{:else}
		<ChatWindow
			onmessage={handleMessage}
			loading={$loading}
			{currentModel}
			models={data.models}
			bind:files
			bind:draft
			onClearContext={handleClearContext}
			onClearTasks={handleClearTasks}
		/>
	{/if}
{:else}
	<div class="mx-auto my-20 max-w-xl rounded-xl border p-6 text-center dark:border-gray-700">
		<h2 class="mb-2 text-xl font-semibold">Backend not configured</h2>
		<p class="text-gray-600 dark:text-gray-300">
			Set BINDU_BASE_URL in your environment to connect to your Bindu backend.
		</p>
	</div>
{/if}
