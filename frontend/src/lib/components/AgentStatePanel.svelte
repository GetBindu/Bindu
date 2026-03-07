<script lang="ts">
	import { onDestroy } from "svelte";
	import Modal from "./Modal.svelte";
	import IconTrash2 from "~icons/lucide/trash-2";

	type FeedbackKind = "success" | "error" | "info";

	interface Props {
		agentName?: string | null;
		/** The agent's context identity, if known */
		contextId?: string | null;
		/** A user-visible session identity (e.g. conversation id), if relevant */
		sessionId?: string | null;
		/** Number of known tasks in this chat/session */
		taskCount?: number;
		disabled?: boolean;
		onClearContext?: () => void | Promise<void>;
		onClearTasks?: () => void | Promise<void>;
	}

	let {
		agentName = null,
		contextId = null,
		sessionId = null,
		taskCount = 0,
		disabled = false,
		onClearContext,
		onClearTasks,
	}: Props = $props();

	let isClearing = $state<"context" | "tasks" | null>(null);
	let feedback = $state<{ kind: FeedbackKind; message: string } | null>(null);
	let feedbackTimeout: ReturnType<typeof setTimeout> | null = $state(null);
	let showConfirm = $state<"context" | "tasks" | null>(null);

	const hasContext = $derived(!!contextId);
	const hasTasks = $derived((taskCount ?? 0) > 0);

	function truncateId(id: string, front = 8, back = 6): string {
		if (id.length <= front + back + 3) return id;
		return `${id.slice(0, front)}...${id.slice(-back)}`;
	}

	function clearFeedbackSoon(ms = 4500) {
		if (feedbackTimeout) clearTimeout(feedbackTimeout);
		feedbackTimeout = setTimeout(() => {
			feedback = null;
			feedbackTimeout = null;
		}, ms);
	}

	async function runClear(target: "context" | "tasks") {
		feedback = null;
		if (feedbackTimeout) {
			clearTimeout(feedbackTimeout);
			feedbackTimeout = null;
		}
		isClearing = target;
		try {
			if (target === "context") {
				await onClearContext?.();
			} else {
				await onClearTasks?.();
			}
			feedback = {
				kind: "success",
				message:
					target === "context"
						? "Context cleared."
						: "Tasks cleared.",
			};
			clearFeedbackSoon(3500);
		} catch (err) {
			feedback = {
				kind: "error",
				message: "Agent is unreachable right now. We reset your UI, but server memory may persist.",
			};
			clearFeedbackSoon(5000);
		} finally {
			isClearing = null;
		}
	}

	const contextStatusLabel = $derived(hasContext ? "Active" : "Empty");

	onDestroy(() => {
		if (feedbackTimeout) clearTimeout(feedbackTimeout);
	});

	function handleKeydown(event: KeyboardEvent) {
		if (event.ctrlKey && event.shiftKey) {
			if (event.key === "C" && hasContext && onClearContext && !disabled) {
				event.preventDefault();
				showConfirm = "context";
			} else if (event.key === "T" && hasTasks && onClearTasks && !disabled) {
				event.preventDefault();
				showConfirm = "tasks";
			}
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="py-2">
	<div class="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">
		Agent inspector
	</div>

	{#if feedback}
		<div
			class="mt-1 text-[10px] font-medium {feedback.kind === 'success'
				? 'text-green-700/90 dark:text-green-300/90'
				: feedback.kind === 'info'
					? 'text-gray-700/80 dark:text-gray-200/80'
					: 'text-yellow-800/90 dark:text-yellow-200/90'}"
		>
			{feedback.message}
		</div>
	{/if}

	<div class="mt-2 space-y-4">
		<!-- Context -->
		<div class="group grid grid-cols-[76px,1fr,auto] items-start gap-2">
			<div class="pt-0.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">
				Context
			</div>
			<div class="min-w-0">
				<div class="text-[12px] font-medium text-gray-800 dark:text-gray-100">{contextStatusLabel}</div>
				<div class="mt-0.5 truncate font-mono text-[11px] text-gray-500 dark:text-gray-400">
					{#if contextId}
						{truncateId(contextId)}
					{:else}
						No agent context yet
					{/if}
				</div>
			</div>
			{#if !disabled && hasContext && onClearContext && isClearing === null}
				<button
					type="button"
					class="mt-0.5 inline-flex items-center rounded p-1 text-gray-400 opacity-0 hover:text-gray-700 focus:opacity-100 focus:outline-none group-hover:opacity-100 dark:text-gray-500 dark:hover:text-gray-200"
					aria-label="Clear context"
					onclick={() => (showConfirm = "context")}
				>
					<IconTrash2 class="size-4" />
				</button>
			{/if}
		</div>

		<!-- Tasks -->
		<div class="group grid grid-cols-[76px,1fr,auto] items-start gap-2">
			<div class="pt-0.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">
				Tasks
			</div>
			<div class="min-w-0">
				<div class="text-[12px] font-medium text-gray-800 dark:text-gray-100">
					{taskCount} {taskCount === 1 ? "task" : "tasks"}
				</div>
			</div>
			{#if !disabled && hasTasks && onClearTasks && isClearing === null}
				<button
					type="button"
					class="mt-0.5 inline-flex items-center rounded p-1 text-gray-400 opacity-0 hover:text-gray-700 focus:opacity-100 focus:outline-none group-hover:opacity-100 dark:text-gray-500 dark:hover:text-gray-200"
					aria-label="Clear tasks"
					onclick={() => (showConfirm = "tasks")}
				>
					<IconTrash2 class="size-4" />
				</button>
			{/if}
		</div>

		<!-- Identity -->
		<div class="grid grid-cols-[76px,1fr] items-start gap-2">
			<div class="pt-0.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">
				Identity
			</div>
			<div class="min-w-0">
				<div
					class="truncate text-[12px] {sessionId
						? 'font-medium text-gray-700 dark:text-gray-200'
						: 'font-normal text-gray-500/90 dark:text-gray-400'}"
				>
					{agentName ?? "Agent"}
				</div>
				<div
					class="mt-0.5 truncate font-mono text-[11px] {sessionId
						? 'text-gray-500 dark:text-gray-400'
						: 'text-gray-400 dark:text-gray-500'}"
				>
					{#if sessionId}
						{truncateId(sessionId)}
					{:else}
						Session not started
					{/if}
				</div>
			</div>
		</div>
	</div>

	<div class="mt-3 text-[9px] text-gray-400/80 dark:text-gray-500/80">
		{#if !hasContext && !hasTasks}
			Nothing to clear yet
		{:else}
			Context and tasks appear once the agent responds
		{/if}
	</div>

</div>

{#if showConfirm}
	<Modal width="max-w-sm" closeOnBackdrop={false} onclose={() => (showConfirm = null)}>
		<div class="p-4">
			<h3 class="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">
				Clear {showConfirm === "context" ? "Context" : "Tasks"}?
			</h3>
			<p class="mb-4 text-sm text-gray-600 dark:text-gray-400">
				{#if showConfirm === "context"}
					This will clear the current agent context. The conversation history will be lost. This action cannot be undone.
				{:else}
					This will clear all tasks. The conversation will continue but task history will be lost. This action cannot be undone.
				{/if}
			</p>
			<div class="flex justify-end gap-2">
				<button
					type="button"
					class="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
					onclick={() => (showConfirm = null)}
				>
					Cancel
				</button>
				<button
					type="button"
					class="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
					onclick={() => {
						const target = showConfirm;
						showConfirm = null;
						if (target) void runClear(target);
					}}
				>
					Clear
				</button>
			</div>
		</div>
	</Modal>
{/if}
