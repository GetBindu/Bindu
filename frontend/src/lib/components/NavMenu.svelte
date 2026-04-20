<script lang="ts" module>
	export const titles: { [key: string]: string } = {
		today: "Today",
		week: "This week",
		month: "This month",
		older: "Older",
	} as const;
</script>

<script lang="ts">
	import { base } from "$app/paths";

	import IconSun from "$lib/components/icons/IconSun.svelte";
	import IconMoon from "$lib/components/icons/IconMoon.svelte";
	import { switchTheme, subscribeToTheme } from "$lib/switchTheme";
	import { isAborted } from "$lib/stores/isAborted";
	import { onDestroy } from "svelte";

	import NavConversationItem from "./NavConversationItem.svelte";
	import ContextList from "./chat/ContextList.svelte";
	import type { LayoutData } from "../../routes/$types";
	import type { ConvSidebar } from "$lib/types/ConvSidebar";
	import { page } from "$app/state";
	import { onMount } from "svelte";
	import { loadContexts, initializeAuth, createNewContext } from "$lib/stores/chat";
	import InfiniteScroll from "./InfiniteScroll.svelte";
	import { CONV_NUM_PER_PAGE } from "$lib/constants/pagination";
	import { browser } from "$app/environment";
	import { usePublicConfig } from "$lib/utils/PublicConfig.svelte";
	import { useAPIClient, handleResponse } from "$lib/APIClient";
	import { requireAuthUser } from "$lib/utils/auth";
	import { isPro } from "$lib/stores/isPro";
	import IconPro from "$lib/components/icons/IconPro.svelte";
	import AgentStatePanel from "$lib/components/AgentStatePanel.svelte";
	import { agentInspector } from "$lib/stores/agentInspector";
	import { slide } from "svelte/transition";
	import { cubicOut } from "svelte/easing";

	const publicConfig = usePublicConfig();
	const client = useAPIClient();

	onMount(() => {
		initializeAuth();
		loadContexts();
	});

	interface Props {
		conversations: ConvSidebar[];
		user: LayoutData["user"];
		p?: number;
		ondeleteConversation?: (id: string) => void;
		oneditConversationTitle?: (payload: { id: string; title: string }) => void;
	}

	let {
		conversations = $bindable(),
		user,
		p = $bindable(0),
		ondeleteConversation,
		oneditConversationTitle,
	}: Props = $props();

	let hasMore = $state(true);
	let showAgentInspector = $state(false);

	function handleNewChatClick(e: MouseEvent) {
		isAborted.set(true);

		// Clear agent context to start fresh
		createNewContext();
		console.log('New Chat clicked - context cleared');

		if (requireAuthUser()) {
			e.preventDefault();
		}
	}

	function handleNavItemClick(e: MouseEvent) {
		if (requireAuthUser()) {
			e.preventDefault();
		}
	}

	const dateRanges = [
		new Date().setDate(new Date().getDate() - 1),
		new Date().setDate(new Date().getDate() - 7),
		new Date().setMonth(new Date().getMonth() - 1),
	];

	let groupedConversations = $derived({
		today: conversations.filter(({ updatedAt }) => updatedAt.getTime() > dateRanges[0]),
		week: conversations.filter(
			({ updatedAt }) => updatedAt.getTime() > dateRanges[1] && updatedAt.getTime() < dateRanges[0]
		),
		month: conversations.filter(
			({ updatedAt }) => updatedAt.getTime() > dateRanges[2] && updatedAt.getTime() < dateRanges[1]
		),
		older: conversations.filter(({ updatedAt }) => updatedAt.getTime() < dateRanges[2]),
	});


	async function handleVisible() {
		p++;
		const newConvs = await client.conversations
			.get({
				query: {
					p,
				},
			})
			.then(handleResponse)
			.then((r) => r.conversations)
			.catch((): ConvSidebar[] => []);

		if (newConvs.length === 0) {
			hasMore = false;
		}

		conversations = [...conversations, ...newConvs];
	}

	$effect(() => {
		if (conversations.length <= CONV_NUM_PER_PAGE) {
			// reset p to 0 if there's only one page of content
			// that would be caused by a data loading invalidation
			p = 0;
		}
	});

	let isDark = $state(false);
	let unsubscribeTheme: (() => void) | undefined;

	if (browser) {
		unsubscribeTheme = subscribeToTheme(({ isDark: nextIsDark }) => {
			isDark = nextIsDark;
		});
	}

	onDestroy(() => {
		unsubscribeTheme?.();
	});
</script>

<div class="flex h-full flex-col">
	<div
		class="sticky top-0 flex flex-none touch-none items-center justify-between px-1.5 py-3.5 max-sm:pt-0"
	>
		<a
			class="nav-app-name select-none rounded-xl text-lg font-bold tracking-tight"
			href="{publicConfig.PUBLIC_ORIGIN}{base}/"
		>
			Bindu

		</a>
		<a
			href={`${base}/`}
			onclick={handleNewChatClick}
			class="new-chat-btn flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium shadow-sm transition-all hover:shadow-none sm:text-smd"
			title="Ctrl/Cmd + Shift + O"
		>
			<svg viewBox="0 0 16 16" fill="currentColor" class="size-3 opacity-70"><path d="M8 1a.75.75 0 0 1 .75.75v5.5h5.5a.75.75 0 0 1 0 1.5h-5.5v5.5a.75.75 0 0 1-1.5 0v-5.5H1.75a.75.75 0 0 1 0-1.5h5.5V1.75A.75.75 0 0 1 8 1Z" /></svg>
			New Chat
		</a>
	</div>

	<div
		class="scrollbar-custom flex flex-grow touch-pan-y flex-col gap-1 overflow-y-auto rounded-r-xl border border-l-0 border-slate-300 bg-slate-100/60 px-3 pb-3 pt-2 text-[.9rem] dark:border-transparent dark:bg-transparent dark:from-gray-800/30 max-sm:bg-gradient-to-t md:bg-gradient-to-l"
	>


		<!-- Agent inspector toggle (collapsed by default) -->
		<div class="nav-section">
			<button
				type="button"
				class="group flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm font-medium text-gray-600 transition-colors duration-150 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700/60 dark:hover:text-white"
				aria-controls="agent-inspector"
				aria-expanded={showAgentInspector}
				onclick={() => (showAgentInspector = !showAgentInspector)}
			>
				<span
					class="inline-flex size-4 shrink-0 items-center justify-center rounded text-gray-400 transition-transform duration-150 motion-reduce:transition-none dark:text-gray-500 {showAgentInspector ? 'rotate-90' : ''}"
					aria-hidden="true"
				>
					<svg viewBox="0 0 20 20" fill="currentColor" class="size-3">
						<path
							fill-rule="evenodd"
							d="M7.21 14.77a.75.75 0 0 1 .02-1.06L10.94 10 7.23 6.29a.75.75 0 1 1 1.06-1.06l4.24 4.24a.75.75 0 0 1 0 1.06l-4.24 4.24a.75.75 0 0 1-1.06-.02Z"
							clip-rule="evenodd"
						/>
					</svg>
				</span>
				<span>Agent Inspector</span>
			</button>
			<p class="px-2.5 pb-1 pl-9 text-[10px] leading-snug text-slate-550 dark:text-slate-500">
				Inspect what the agent remembers and is working on
			</p>
		</div>
		{#if showAgentInspector}
			<div
				id="agent-inspector"
				class="pl-2.5"
				transition:slide|local={{ duration: 120, easing: cubicOut }}
			>
				<AgentStatePanel
					agentName={$agentInspector.agentName}
					contextId={$agentInspector.contextId}
					sessionId={$agentInspector.sessionId}
					taskCount={$agentInspector.taskCount}
					disabled={$agentInspector.disabled}
					onClearContext={$agentInspector.onClearContext}
					onClearTasks={$agentInspector.onClearTasks}
				/>
			</div>
		{/if}

		<!-- Agent Contexts Section -->
		<ContextList />
	</div>

	<div
		class="mt-auto flex touch-none flex-col gap-1 rounded-r-xl border border-l-0 border-slate-200/60 bg-slate-50/80 p-3 text-sm dark:border-transparent dark:bg-transparent md:bg-gradient-to-l md:dark:from-gray-800/30"
	>

		{#if user?.username || user?.email}
			<div
				class="group flex items-center gap-1.5 rounded-lg pl-2.5 pr-2 hover:bg-gray-100 first:hover:bg-transparent dark:hover:bg-gray-700 first:dark:hover:bg-transparent"
			>
				<span
					class="flex h-9 flex-none shrink items-center gap-1.5 truncate pr-2 text-slate-600 dark:text-gray-400"
					>{user?.username || user?.email}</span
				>

				{#if publicConfig.isHuggingChat && $isPro === false}
					<a
						href="https://huggingface.co/subscribe/pro?from=HuggingChat"
						target="_blank"
						rel="noopener noreferrer"
						class="ml-auto flex h-[20px] items-center gap-1 px-1.5 py-0.5 text-xs text-gray-500 dark:text-gray-400"
					>
						<IconPro />
						Get PRO
					</a>
				{:else if publicConfig.isHuggingChat && $isPro === true}
					<span
						class="ml-auto flex h-[20px] items-center gap-1 px-1.5 py-0.5 text-xs text-gray-500 dark:text-gray-400"
					>
						<IconPro />
						PRO
					</span>
				{/if}

				<img
					src="https://huggingface.co/api/users/{user.username}/avatar?redirect=true"
					class="{!(publicConfig.isHuggingChat && $isPro !== null)
						? 'ml-auto'
						: ''} size-4 rounded-full border bg-gray-500 dark:border-white/40"
					alt=""
				/>
			</div>
		{/if}

		<span class="flex gap-1">
			<a
				href="{base}/settings/application"
				class="flex h-9 flex-none flex-grow items-center gap-1.5 rounded-lg pl-2.5 pr-2 text-slate-600 transition-colors duration-150 hover:bg-gray-100 hover:text-slate-900 dark:text-gray-400 dark:hover:bg-gray-700/60 dark:hover:text-gray-200"
				onclick={handleNavItemClick}
			>
				<svg viewBox="0 0 20 20" fill="currentColor" class="size-4 opacity-60"><path fill-rule="evenodd" d="M7.84 1.804A1 1 0 0 1 8.82 1h2.36a1 1 0 0 1 .98.804l.331 1.652a6.993 6.993 0 0 1 1.929 1.115l1.598-.54a1 1 0 0 1 1.186.447l1.18 2.044a1 1 0 0 1-.205 1.251l-1.267 1.113a7.047 7.047 0 0 1 0 2.228l1.267 1.113a1 1 0 0 1 .206 1.25l-1.18 2.045a1 1 0 0 1-1.187.447l-1.598-.54a6.993 6.993 0 0 1-1.929 1.115l-.33 1.652a1 1 0 0 1-.98.804H8.82a1 1 0 0 1-.98-.804l-.331-1.652a6.993 6.993 0 0 1-1.929-1.115l-1.598.54a1 1 0 0 1-1.186-.447l-1.18-2.044a1 1 0 0 1 .205-1.251l1.267-1.114a7.05 7.05 0 0 1 0-2.227L1.821 7.773a1 1 0 0 1-.206-1.25l1.18-2.045a1 1 0 0 1 1.187-.447l1.598.54A6.992 6.992 0 0 1 7.51 3.456l.33-1.652ZM10 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" clip-rule="evenodd" /></svg>
				Settings
			</a>
			<button
				onclick={() => {
					switchTheme();
				}}
				aria-label="Toggle theme"
				class="flex size-9 min-w-[1.5em] flex-none items-center justify-center rounded-lg p-2 text-gray-500 transition-colors duration-150 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700/60 dark:hover:text-gray-200"
			>
				{#if browser}
					{#if isDark}
						<IconSun />
					{:else}
						<IconMoon />
					{/if}
				{/if}
			</button>
		</span>
	</div>
</div>


<style>
	.nav-app-name {
		background: linear-gradient(135deg, #111827 0%, #374151 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	:global(.dark) .nav-app-name {
		background: linear-gradient(135deg, #f1f5f9 0%, #a78bfa 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.new-chat-btn {
		background: white;
		border-color: #e5e7eb;
		color: #374151;
	}

	.new-chat-btn:hover {
		background: #f9fafb;
		border-color: #d1d5db;
	}

	:global(.dark) .new-chat-btn {
		background: rgba(55, 65, 81, 0.8);
		border-color: rgba(75, 85, 99, 0.8);
		color: #d1d5db;
	}

	:global(.dark) .new-chat-btn:hover {
		background: rgba(75, 85, 99, 0.9);
		border-color: rgba(107, 114, 128, 0.8);
	}

	.nav-section {
		border-bottom: 1px solid rgba(0, 0, 0, 0.05);
		padding-bottom: 0.25rem;
		margin-bottom: 0.25rem;
	}

	:global(.dark) .nav-section {
		border-bottom-color: rgba(255, 255, 255, 0.05);
	}
</style>
