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

	$effect(() => {
		if (browser && !agentContextsLoaded) {
			loadAgentContexts();
		}
	});

	async function loadAgentContexts() {
		try {
			const token = localStorage.getItem("bindu_oauth_token");
			agentAPI.setAuthToken(token ?? null);

			const contexts = await agentAPI.listContexts(50);
			const agentConvs = [];

			for (const ctx of contexts) {
				let title = "New Chat";
				let timestamp = new Date();

				if (ctx.task_ids?.length > 0) {
					try {
						const task = await agentAPI.getTask(ctx.task_ids[0]);
						const history = task.history || [];

						for (const msg of history) {
							if (msg.role === "user") {
								const text = msg.parts
									?.filter((p) => p.kind === "text")
									?.map((p) => p.text)
									?.[0];
								if (text) {
									title = text.slice(0, 50) + (text.length > 50 ? "..." : "");
									break;
								}
							}
						}

						if (task.status?.timestamp) {
							timestamp = new Date(task.status.timestamp);
						}
					} catch {}
				}

				if (ctx.context_id) {
					agentConvs.push({
						id: ctx.context_id,
						title,
						model: "bindu",
						updatedAt: timestamp
					});
				}
			}

			conversations = [...data.conversations, ...agentConvs].sort(
				(a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()
			);

			agentContextsLoaded = true;
		} catch {}
	}

	let isNavCollapsed = $state(false);
	let errorToastTimeout: ReturnType<typeof setTimeout>;
	let currentError: string | undefined = $state();

	const settings = createSettingsStore(data.settings);

	onDestroy(() => clearTimeout(errorToastTimeout));
</script>

<svelte:head>
	<title>{publicConfig.PUBLIC_APP_NAME}</title>
</svelte:head>

<!-- ✅ SKIP LINK ADDED -->
<a href="#main-content" class="skip-link">Skip to Content</a>

<BackgroundGenerationPoller />

<div class="fixed grid h-full w-screen grid-cols-1 grid-rows-[auto,1fr] overflow-hidden text-smd">

	<MobileNav>
		<NavMenu {conversations} user={data.user} />
	</MobileNav>

	<nav class="max-md:hidden">
		<NavMenu {conversations} user={data.user} />
	</nav>

	{#if currentError}
		<Toast message={currentError} />
	{/if}

	<!-- ✅ MAIN WRAPPER ADDED -->
	<main id="main-content" class="contents">
		{@render children?.()}
	</main>

	<Footer />
</div>

<!-- ✅ ACCESSIBILITY STYLES -->
<style>
.skip-link {
	position: absolute;
	top: -60px;
	left: 16px;
	background: black;
	color: white;
	padding: 8px 14px;
	border-radius: 6px;
	text-decoration: none;
	font-weight: 500;
	z-index: 10000;
	transition: top 0.2s ease;
}

.skip-link:focus {
	top: 16px;
	outline: 2px solid white;
}
</style>