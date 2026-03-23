<script lang="ts">
	import { onMount } from "svelte";
	import { base } from "$app/paths";
	import { afterNavigate, goto } from "$app/navigation";
	import { page } from "$app/state";
	import IconBurger from "$lib/components/icons/IconBurger.svelte";
	import CarbonClose from "~icons/carbon/close";
	import CarbonChevronLeft from "~icons/carbon/chevron-left";
	import IconGear from "~icons/bi/gear-fill";

	import type { LayoutData } from "../$types";
	import { browser } from "$app/environment";
	import { isDesktop } from "$lib/utils/isDesktop";
	import { debounce } from "$lib/utils/debounce";

	// Agent card types for sidebar
	type AgentSkill = { id: string; name: string };
	type AgentCard = { name: string; skills?: AgentSkill[] };
	let agentCard = $state<AgentCard | null>(null);
	let agentLoading = $state(true);

	interface Props {
		data: LayoutData;
		children?: import("svelte").Snippet;
	}

	let { data, children }: Props = $props();

	let previousPage: string = $state(base || "/");
	let showContent: boolean = $state(false);

	function checkDesktopRedirect() {
		if (
			browser &&
			isDesktop(window) &&
			page.url.pathname === `${base}/settings`
		) {
			goto(`${base}/settings/agent`);
		}
	}

	onMount(() => {
		// Fetch agent card for sidebar
		(async () => {
			try {
				const res = await fetch("/api/agent-card");
				if (res.ok) {
					agentCard = await res.json();
				}
			} catch (e) {
				// ignore
			} finally {
				agentLoading = false;
			}
		})();

		// Show content when not on the root settings page
		showContent = page.url.pathname !== `${base}/settings`;
		// Initial desktop redirect check
		checkDesktopRedirect();

		// Add resize listener for desktop redirect
		if (browser) {
			const debouncedCheck = debounce(checkDesktopRedirect, 100);
			window.addEventListener("resize", debouncedCheck);
			return () => window.removeEventListener("resize", debouncedCheck);
		}
	});

	afterNavigate(({ from }) => {
		if (from?.url && !from.url.pathname.includes("settings")) {
			previousPage = from.url.toString() || previousPage || base || "/";
		}
		// Show content when not on the root settings page
		showContent = page.url.pathname !== `${base}/settings`;
		// Check desktop redirect after navigation
		checkDesktopRedirect();
	});
</script>

<div
	class="mx-auto grid h-full w-full max-w-[1400px] grid-cols-1 grid-rows-[auto,1fr] content-start gap-x-6 overflow-hidden p-4 text-gray-800 dark:text-gray-300 md:grid-cols-3 md:grid-rows-[auto,1fr] md:p-4"
>
	<div class="col-span-1 mb-3 flex items-center justify-between md:col-span-3 md:mb-4">
		{#if showContent && browser}
			<button
				class="btn rounded-lg md:hidden"
				aria-label="Back to menu"
				onclick={() => {
					showContent = false;
					goto(`${base}/settings`);
				}}
			>
				<IconBurger
					classNames="text-xl text-gray-900 hover:text-black dark:text-gray-200 dark:hover:text-white sm:hidden"
				/>
				<CarbonChevronLeft
					class="text-xl text-gray-900 hover:text-black dark:text-gray-200 dark:hover:text-white max-sm:hidden"
				/>
			</button>
		{/if}
		<h2 class=" left-0 right-0 mx-auto w-fit text-center text-xl font-bold md:hidden">Settings</h2>
		<button
			class="btn rounded-lg"
			aria-label="Close settings"
			onclick={() => {
				goto(previousPage);
			}}
		>
			<CarbonClose
				class="text-xl text-gray-900 hover:text-black dark:text-gray-200 dark:hover:text-white"
			/>
		</button>
	</div>
	{#if !(showContent && browser && !isDesktop(window))}
		<div
			class="scrollbar-custom col-span-1 flex flex-col overflow-y-auto whitespace-nowrap rounded-r-xl bg-gradient-to-l from-gray-50 to-10% dark:from-gray-700/40 max-md:-mx-4 max-md:h-full md:pr-6"
			class:max-md:hidden={showContent && browser}
		>
			<!-- Agent Info -->
			<button
				type="button"
				onclick={() => goto(`${base}/settings/agent`)}
				class="group flex h-9 w-full flex-none items-center gap-1 rounded-lg px-3 text-[13px] text-gray-600 dark:text-gray-300 md:rounded-xl md:px-3 {page
					.url.pathname === `${base}/settings/agent`
					? '!bg-gray-100 !text-gray-800 dark:!bg-gray-700 dark:!text-gray-200'
					: 'bg-white dark:bg-gray-800'}"
				aria-label="View agent info"
			>
				<span class="mr-1 size-2 rounded-full bg-green-500"></span>
				Agent Info
			</button>

			<!-- Skills -->
			{#if agentLoading}
				<div class="px-3 py-2 text-xs text-gray-400">Loading skills...</div>
			{:else if agentCard?.skills && agentCard.skills.length > 0}
				<div class="mb-1 mt-3 px-3 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
					Skills
				</div>
				{#each agentCard.skills as skill}
					<button
						type="button"
						onclick={() => goto(`${base}/settings/skill/${skill.id}`)}
						class="group flex h-9 w-full flex-none items-center gap-1 rounded-lg px-3 text-[13px] text-gray-600 dark:text-gray-300 md:rounded-xl md:px-3 {page
							.url.pathname === `${base}/settings/skill/${skill.id}`
							? '!bg-gray-100 !text-gray-800 dark:!bg-gray-700 dark:!text-gray-200'
							: 'bg-white dark:bg-gray-800'}"
						aria-label="View skill {skill.name}"
					>
						<span
							class="rounded bg-green-100 px-1 py-0.5 text-[9px] font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
							>fn</span
						>
						<span class="truncate">{skill.name}</span>
					</button>
				{/each}
			{/if}

			<!-- Settings -->
			<div class="mb-1 mt-3 px-3 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
				Preferences
			</div>
			<button
				type="button"
				onclick={() => goto(`${base}/settings/authentication`)}
				class="group flex h-9 w-full flex-none items-center gap-1 rounded-lg px-3 text-[13px] text-gray-600 dark:text-gray-300 md:rounded-xl md:px-3 {page
					.url.pathname === `${base}/settings/authentication`
					? '!bg-gray-100 !text-gray-800 dark:!bg-gray-700 dark:!text-gray-200'
					: 'bg-white dark:bg-gray-800'}"
				aria-label="Authentication"
			>
				<span class="mr-0.5 text-xs">🔐</span>
				Authentication
			</button>
			<button
				type="button"
				onclick={() => goto(`${base}/settings/negotiation`)}
				class="group flex h-9 w-full flex-none items-center gap-1 rounded-lg px-3 text-[13px] text-gray-600 dark:text-gray-300 md:rounded-xl md:px-3 {page
					.url.pathname === `${base}/settings/negotiation`
					? '!bg-gray-100 !text-gray-800 dark:!bg-gray-700 dark:!text-gray-200'
					: 'bg-white dark:bg-gray-800'}"
				aria-label="Negotiation"
			>
				<span class="mr-0.5 text-xs">🤝</span>
				Negotiation
			</button>
			<button
				type="button"
				onclick={() => goto(`${base}/settings/did-resolve`)}
				class="group flex h-9 w-full flex-none items-center gap-1 rounded-lg px-3 text-[13px] text-gray-600 dark:text-gray-300 md:rounded-xl md:px-3 {page
					.url.pathname === `${base}/settings/did-resolve`
					? '!bg-gray-100 !text-gray-800 dark:!bg-gray-700 dark:!text-gray-200'
					: 'bg-white dark:bg-gray-800'}"
				aria-label="DID Resolve"
			>
				<span class="mr-0.5 text-xs">🔍</span>
				DID Resolve
			</button>
			<button
				type="button"
				onclick={() => goto(`${base}/settings/application`)}
				class="group flex h-9 w-full flex-none items-center gap-1 rounded-lg px-3 text-[13px] text-gray-600 dark:text-gray-300 md:rounded-xl md:px-3 {page
					.url.pathname === `${base}/settings/application`
					? '!bg-gray-100 !text-gray-800 dark:!bg-gray-700 dark:!text-gray-200'
					: 'bg-white dark:bg-gray-800'}"
				aria-label="Configure settings"
			>
				<IconGear class="mr-0.5 text-xxs" />
				Settings
			</button>
		</div>
	{/if}
	{#if showContent}
		<div
			class="scrollbar-custom col-span-1 w-full overflow-y-auto overflow-x-clip px-1 md:col-span-2 md:row-span-2"
			class:max-md:hidden={!showContent && browser}
		>
			{@render children?.()}
		</div>
	{/if}
</div>
