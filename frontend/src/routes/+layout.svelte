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

	// ⭐ PRO CONSTANTS (no magic numbers)
	const MAX_CONTEXTS = 50;
	const TITLE_LIMIT = 50;
	const DEFAULT_TITLE = "New Chat";

	$effect(() => {
		data.conversations && untrack(() => (conversations = data.conversations));
	});

	// Load agent contexts client-side
	$effect(() => {
		if (browser && !agentContextsLoaded) {
			loadAgentContexts();
		}
	});

	// (Optimized)
	async function loadAgentContexts() {
		try {
			// SSR safe token handling
			const token = localStorage?.getItem("bindu_oauth_token") ?? null;
			agentAPI.setAuthToken(token);

			const contexts = await agentAPI.listContexts(MAX_CONTEXTS);

			if (!contexts?.length) {
				agentContextsLoaded = true;
				return;
			}

			// Parallel task fetching
			const agentConvs = await Promise.all(
				contexts.map(async (ctx) => {
					if (!ctx?.context_id) return null;

					let title = DEFAULT_TITLE;
					let timestamp = new Date();

					if (!ctx.task_ids?.length) {
						return {
							id: ctx.context_id,
							title,
							model: "bindu",
							updatedAt: timestamp,
						};
					}

					try {
						const task = await agentAPI.getTask(ctx.task_ids[0]);

						const userMsg = task?.history?.find(
							(msg) => msg.role === "user"
						);

						const text = userMsg?.parts
							?.filter((p) => p.kind === "text")
							?.[0]?.text;

						if (text) {
							title =
								text.slice(0, TITLE_LIMIT) +
								(text.length > TITLE_LIMIT ? "..." : "");
						}

						if (task?.status?.timestamp) {
							timestamp = new Date(task.status.timestamp);
						}
					} catch (err) {
						console.error("Context preview load failed:", err);
					}

					return {
						id: ctx.context_id,
						title,
						model: "bindu",
						updatedAt: timestamp,
					};
				})
			);

			// Remove nulls
			const validAgentConvs = agentConvs.filter(Boolean);

			// Prevent duplicates
			const unique = new Map();
			[...data.conversations, ...validAgentConvs].forEach((conv) =>
				unique.set(conv.id, conv)
			);

			conversations = [...unique.values()].sort(
				(a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()
			);

			agentContextsLoaded = true;
		} catch (err) {
			console.error("Error loading agent contexts:", err);
			$error = "Failed to load conversations";
		}
	}

	let isNavCollapsed = $state(false);

	let errorToastTimeout: ReturnType<typeof setTimeout>;
	let currentError: string | undefined = $state();

	async function onError() {
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
				conversations = conversations.map((conv) =>
					conv.id === id ? { ...conv, title } : conv
				);
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
				.catch(() => {});
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

		const onKeydown = (e: KeyboardEvent) => {
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

	let showWelcome = $derived(
		!$settings.welcomeModalSeen &&
			!(page.data.shared === true && page.route.id?.startsWith("/conversation/"))
	);
</script>
