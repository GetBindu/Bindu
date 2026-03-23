<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { contexts, contextId, clearContext, switchContext } from '$lib/stores/chat';
	import type { Context } from '$lib/types/agent';

	function formatTime(timestamp: number): string {
		const date = new Date(timestamp);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const hours = Math.floor(diff / (1000 * 60 * 60));

		if (hours < 24) {
			return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
		} else {
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		}
	}

	function getContextColor(index: number): string {
		const colors = ['blue', 'green', 'purple', 'orange', 'pink'];
		return colors[index % colors.length];
	}

	async function handleSwitchContext(ctxId: string) {
		await switchContext(ctxId);
		goto(`${base}/`);
	}

	function handleClearContext(event: Event, ctxId: string) {
		event.stopPropagation();
		if (confirm('Are you sure you want to clear this context? This action cannot be undone.')) {
			clearContext(ctxId);
		}
	}

	$: sortedContexts = [...$contexts].sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
	$: activeContextId = $contextId;
</script>

<div class="flex flex-col gap-0.5">
	{#if sortedContexts.length === 0}
		<div class="px-2 py-4 text-center text-xs text-gray-400 dark:text-gray-500">
			No agent contexts yet
		</div>
	{:else}
		{#each sortedContexts as ctx, index (ctx.id)}
			<button
				type="button"
				class="group relative flex flex-col gap-1 rounded-lg px-2.5 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 {ctx.id === activeContextId ? 'bg-gray-100 dark:bg-gray-700' : ''}"
				on:click={() => handleSwitchContext(ctx.id)}
			>
				<div class="flex items-center gap-2">
					<span class="truncate font-medium text-gray-900 dark:text-gray-100">
						{ctx.firstMessage || 'New conversation'}
					</span>
					<div
						role="button"
						tabindex="0"
						class="ml-auto hidden size-5 items-center justify-center rounded hover:bg-gray-200 group-hover:flex dark:hover:bg-gray-600 cursor-pointer"
						on:click={(e) => handleClearContext(e, ctx.id)}
						on:keydown={(e) => e.key === 'Enter' && handleClearContext(e, ctx.id)}
						title="Clear context"
					>
						<span class="text-xs text-gray-500 dark:text-gray-400">×</span>
					</div>
				</div>
				<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
					<span>{ctx.taskCount || 0} task{(ctx.taskCount || 0) !== 1 ? 's' : ''}</span>
					<span>•</span>
					<span class="font-mono">{ctx.id.substring(0, 8)}</span>
					{#if ctx.timestamp}
						<span class="ml-auto">{formatTime(ctx.timestamp)}</span>
					{/if}
				</div>
			</button>
		{/each}
	{/if}
</div>
