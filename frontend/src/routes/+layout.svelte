<script lang="ts">
	import "../styles/main.css";

	import { onDestroy, onMount, untrack } from "svelte";
	import { goto } from "$app/navigation";
	import { base } from "$app/paths";
	import { page } from "$app/state";

	import { error } from "$lib/stores/errors";
	import { createSettingsStore } from "$lib/stores/settings";
	import { loading } from "$lib/stores/loading";

	import Toast from "$lib/components/Toast.svelte";
	import NavMenu from "$lib/components/NavMenu.svelte";
	import MobileNav from "$lib/components/MobileNav.svelte";
	import titleUpdate from "$lib/stores/titleUpdate";
	import WelcomeModal from "$lib/components/WelcomeModal.svelte";
	import Footer from "$lib/components/Footer.svelte";
	import ExpandNavigation from "$lib/components/ExpandNavigation.svelte";
	import { setContext } from "svelte";
	import { handleResponse, useAPIClient } from "$lib/APIClient";
	import { isAborted } from "$lib/stores/isAborted";
	import { isPro } from "$lib/stores/isPro";
	import IconShare from "$lib/components/icons/IconShare.svelte";
	import { shareModal } from "$lib/stores/shareModal";
	import BackgroundGenerationPoller from "$lib/components/BackgroundGenerationPoller.svelte";
	import { requireAuthUser } from "$lib/utils/auth";
	import { agentAPI } from "$lib/services/agent-api";
	import { browser } from "$app/environment";

	let { data = $bindable(), children } = $props();

	setContext("publicConfig", data.publicConfig);

	const publicConfig = data.publicConfig;
	const client = useAPIClient();

	let conversations = $state(data.conversations);
	let agentContextsLoaded = $state(false);

	$effect(() => {
		data.conversations && untrack(() => (conversations = data.conversations));
	});

	// Load agent contexts client-side
	$effect(() => {
		if (browser && !agentContextsLoaded) {
			loadAgentContexts();
		}
	});

	async function loadAgentContexts() {
		try {
			console.log('Loading agent contexts...');
			const token = localStorage.getItem('bindu_oauth_token');
			if (token) {
				console.log('Token found, setting auth token...');
				agentAPI.setAuthToken(token);
			} else {
				console.log('No OAuth token found, continuing without auth (auth is optional)');
				agentAPI.setAuthToken(null);
			}

			console.log('Fetching contexts...');
			const contexts = await agentAPI.listContexts(50);
			console.log('Contexts received:', contexts);
			console.log('Number of contexts:', contexts.length);

			const agentConvs = [];
			for (let i = 0; i < contexts.length; i++) {
				const ctx = contexts[i];
				console.log(`Processing context ${i + 1}/${contexts.length}:`, ctx);
				let title = 'New Chat';
				let timestamp = new Date();

				if (ctx.task_ids && ctx.task_ids.length > 0) {
					console.log(`  Context has ${ctx.task_ids.length} tasks, fetching first task:`, ctx.task_ids[0]);
					try {
						const task = await agentAPI.getTask(ctx.task_ids[0]);
						console.log('  Task received:', task);
						const history = task.history || [];
						console.log('  Task history length:', history.length);

						for (const msg of history) {
							if (msg.role === 'user') {
								const parts = msg.parts || [];
								const textParts = parts
									.filter(part => part.kind === 'text')
									.map(part => part.text || '');
								if (textParts.length > 0) {
									title = textParts[0].substring(0, 50);
									if (textParts[0].length > 50) title += '...';
									console.log('  ✅ Found title:', title);
									break;
								}
							}
						}

						if (task.status && task.status.timestamp) {
							timestamp = new Date(task.status.timestamp);
						}
					} catch (err) {
						console.error('  ❌ Error loading context preview:', err);
					}
				} else {
					console.log('  No tasks in this context');
				}

				console.log(`  Final title for context: "${title}"`);

				if (ctx.context_id) {
					agentConvs.push({
						id: ctx.context_id,
						title,
						model: 'bindu',
						updatedAt: timestamp,
					});
				}
			}

			console.log('Agent conversations to add:', agentConvs);

			// Merge and sort
			conversations = [...data.conversations, ...agentConvs].sort(
				(a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()
			);
			console.log('Final merged conversations:', conversations);
			agentContextsLoaded = true;
		} catch (err) {
			console.error('Error loading agent contexts:', err);
		}
	}

	let isNavCollapsed = $state(false);

	let errorToastTimeout: ReturnType<typeof setTimeout>;
	let currentError: string | undefined = $state();

	async function onError() {
		// If a new different error comes, wait for the current error to hide first
		if ($error && currentError && $error !== currentError) {
			clearTimeout(errorToastTimeout);
			currentError = undefined;
			await new Promise((resolve) => setTimeout(resolve, 300));
		}

		currentError = $error;

		errorToastTimeout = setTimeout(() => {
			$error = undefined;
			currentError = undefined;
		}, 5000);
	}

	let canShare = $derived(
		publicConfig.isHuggingChat &&
			Boolean(page.params?.id) &&
			page.route.id?.startsWith("/conversation/")
	);

	async function deleteConversation(id: string) {
		client
			.conversations({ id })
			.delete()
			.then(handleResponse)
			.then(async () => {
				conversations = conversations.filter((conv) => conv.id !== id);

				if (page.params.id === id) {
					await goto(`${base}/`, { invalidateAll: true });
				}
			})
			.catch((err) => {
				console.error(err);
				$error = String(err);
			});
	}

	async function editConversationTitle(id: string, title: string) {
		client
			.conversations({ id })
			.patch({ title })
			.then(handleResponse)
			.then(async () => {
				conversations = conversations.map((conv) => (conv.id === id ? { ...conv, title } : conv));
			})
			.catch((err) => {
				console.error(err);
				$error = String(err);
			});
	}

	function closeWelcomeModal() {
		if (requireAuthUser()) return;
		settings.set({ welcomeModalSeen: true });
	}

	onDestroy(() => {
		clearTimeout(errorToastTimeout);
	});

	$effect(() => {
		if ($error) onError();
	});

	$effect(() => {
		if ($titleUpdate) {
			const convIdx = conversations.findIndex(({ id }) => id === $titleUpdate?.convId);

			if (convIdx != -1) {
				conversations[convIdx].title = $titleUpdate?.title ?? conversations[convIdx].title;
			}

			$titleUpdate = null;
		}
	});

	const settings = createSettingsStore(data.settings);

	onMount(async () => {
		if (publicConfig.isHuggingChat && data.user?.username) {
			fetch(`https://huggingface.co/api/users/${data.user.username}/overview`)
				.then((res) => res.json())
				.then((userData) => {
					isPro.set(userData.isPro ?? false);
				})
				.catch(() => {
					// Keep isPro as null on error - don't show any badge if status is unknown
				});
		}

		if (page.url.searchParams.has("token")) {
			const token = page.url.searchParams.get("token");

			await fetch(`${base}/api/user/validate-token`, {
				method: "POST",
				body: JSON.stringify({ token }),
			}).then(() => {
				goto(`${base}/`, { invalidateAll: true });
			});
		}

		// Global keyboard shortcut: New Chat (Ctrl/Cmd + Shift + O)
		const onKeydown = (e: KeyboardEvent) => {
			// Ignore when a modal has focus (app is inert)
			const appEl = document.getElementById("app");
			if (appEl?.hasAttribute("inert")) return;

			const oPressed = e.key?.toLowerCase() === "o";
			const metaOrCtrl = e.metaKey || e.ctrlKey;
			if (oPressed && e.shiftKey && metaOrCtrl) {
				e.preventDefault();
				isAborted.set(true);
				if (requireAuthUser()) return;
				goto(`${base}/`, { invalidateAll: true });
			}
		};

		window.addEventListener("keydown", onKeydown, { capture: true });
		onDestroy(() => window.removeEventListener("keydown", onKeydown, { capture: true }));
	});

	let mobileNavTitle = $derived(
		["/privacy"].includes(page.route.id ?? "")
			? ""
			: conversations.find((conv) => conv.id === page.params.id)?.title
	);

	// Show the welcome modal once on first app load
	let showWelcome = $derived(
		!$settings.welcomeModalSeen &&
			!(page.data.shared === true && page.route.id?.startsWith("/conversation/"))
	);
</script>

<svelte:head>
	<title>{publicConfig.PUBLIC_APP_NAME}</title>
	<meta name="description" content={publicConfig.PUBLIC_APP_DESCRIPTION} />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:site" content="@huggingface" />
	<meta name="twitter:title" content={publicConfig.PUBLIC_APP_NAME} />
	<meta name="twitter:description" content={publicConfig.PUBLIC_APP_DESCRIPTION} />
	<meta
		name="twitter:image"
		content="{publicConfig.PUBLIC_ORIGIN || page.url.origin}{publicConfig.assetPath}/thumbnail.png"
	/>
	<meta name="twitter:image:alt" content="{publicConfig.PUBLIC_APP_NAME} preview" />

	<meta property="og:title" content={publicConfig.PUBLIC_APP_NAME} />
	<meta property="og:type" content="website" />
	<meta property="og:url" content="{publicConfig.PUBLIC_ORIGIN || page.url.origin}{base}" />
	<meta property="og:image" content="{publicConfig.assetPath}/thumbnail.png" />
	<meta property="og:description" content={publicConfig.PUBLIC_APP_DESCRIPTION} />
	<meta property="og:site_name" content={publicConfig.PUBLIC_APP_NAME} />
	<meta property="og:locale" content="en_US" />
	<link rel="icon" href="{publicConfig.assetPath}/icon.svg" type="image/svg+xml" />
	{#if publicConfig.PUBLIC_ORIGIN}
		<link
			rel="icon"
			href="{publicConfig.assetPath}/favicon.svg"
			type="image/svg+xml"
			media="(prefers-color-scheme: light)"
		/>
		<link
			rel="icon"
			href="{publicConfig.assetPath}/favicon-dark.svg"
			type="image/svg+xml"
			media="(prefers-color-scheme: dark)"
		/>
	{:else}
		<link rel="icon" href="{publicConfig.assetPath}/favicon-dev.svg" type="image/svg+xml" />
	{/if}
	<link rel="apple-touch-icon" href="{publicConfig.assetPath}/apple-touch-icon.png" />
	<link rel="manifest" href="{publicConfig.assetPath}/manifest.json" />

	{#if publicConfig.PUBLIC_PLAUSIBLE_SCRIPT_URL}
		<script async src={publicConfig.PUBLIC_PLAUSIBLE_SCRIPT_URL}></script>
	{/if}

	{#if publicConfig.PUBLIC_APPLE_APP_ID}
		<meta name="apple-itunes-app" content={`app-id=${publicConfig.PUBLIC_APPLE_APP_ID}`} />
	{/if}
</svelte:head>

{#if showWelcome}
	<WelcomeModal close={closeWelcomeModal} />
{/if}

<BackgroundGenerationPoller />

<div
	class="fixed grid h-full w-screen grid-cols-1 grid-rows-[auto,1fr] overflow-hidden text-smd {!isNavCollapsed
		? 'md:grid-cols-[290px,1fr]'
		: 'md:grid-cols-[0px,1fr]'} transition-[300ms] [transition-property:grid-template-columns] dark:text-gray-300 md:grid-rows-[1fr]"
>
	<ExpandNavigation
		isCollapsed={isNavCollapsed}
		onClick={() => (isNavCollapsed = !isNavCollapsed)}
		classNames="absolute inset-y-0 z-10 my-auto {!isNavCollapsed
			? 'left-[290px]'
			: 'left-0'} *:transition-transform"
	/>

	{#if canShare}
		<button
			type="button"
			class="hidden size-8 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white/90 text-sm font-medium text-gray-700 shadow-sm hover:bg-white/60 hover:text-gray-500 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-200 dark:hover:bg-gray-700 md:absolute md:right-6 md:top-5 md:flex
				{$loading ? 'cursor-not-allowed opacity-40' : ''}"
			onclick={() => shareModal.open()}
			aria-label="Share conversation"
			disabled={$loading}
		>
			<IconShare />
		</button>
	{/if}

	<MobileNav title={mobileNavTitle}>
		<NavMenu
			{conversations}
			user={data.user}
			ondeleteConversation={(id) => deleteConversation(id)}
			oneditConversationTitle={(payload) => editConversationTitle(payload.id, payload.title)}
		/>
	</MobileNav>
	<nav
		class="grid max-h-dvh grid-cols-1 grid-rows-[auto,1fr,auto] overflow-hidden *:w-[290px] max-md:hidden"
	>
		<NavMenu
			{conversations}
			user={data.user}
			ondeleteConversation={(id) => deleteConversation(id)}
			oneditConversationTitle={(payload) => editConversationTitle(payload.id, payload.title)}
		/>
	</nav>
	{#if currentError}
		<Toast message={currentError} />
	{/if}
	{@render children?.()}

	<Footer />

	{#if publicConfig.PUBLIC_PLAUSIBLE_SCRIPT_URL}
		<script>
			(window.plausible =
				window.plausible ||
				function () {
					(plausible.q = plausible.q || []).push(arguments);
				}),
				(plausible.init =
					plausible.init ||
					function (i) {
						plausible.o = i || {};
					});
			plausible.init();
		</script>
	{/if}
</div>
