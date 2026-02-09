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

	let { data } = $props();

	let hasModels = $derived(Boolean(data.models?.length));
	let files: File[] = $state([]);
	let draft = $state("");

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
</script>

<svelte:head>
	<title>{publicConfig.PUBLIC_APP_NAME}</title>
</svelte:head>

{#if hasModels}
	<ChatWindow
		onmessage={(message) => createConversation(message)}
		loading={$loading}
		{currentModel}
		models={data.models}
		bind:files
		bind:draft
	/>
{:else}
	<div class="mx-auto my-20 max-w-xl rounded-xl border p-6 text-center dark:border-gray-700">
		<h2 class="mb-2 text-xl font-semibold">Backend not configured</h2>
		<p class="text-gray-600 dark:text-gray-300">
			Set BINDU_BASE_URL in your environment to connect to your Bindu backend.
		</p>
	</div>
{/if}
