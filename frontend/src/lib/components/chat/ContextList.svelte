<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { contexts, contextId, clearContext, switchContext } from '$lib/stores/chat';

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
		<div class="px-2 py-4 text-center text-xs text-slate-400/70">
			No agent contexts yet
		</div>
	{:else}
		{#each sortedContexts as ctx (ctx.id)}
			<button
				type="button"
				class="group relative flex flex-col gap-1 rounded-lg border transition-colors duration-150 px-2.5 py-2 text-left text-sm
				{ctx.id === activeContextId
					? 'border-slate-300 bg-white shadow-sm dark:border-white/15 dark:bg-white/10 dark:shadow-none'
					: 'border-transparent hover:border-slate-200 hover:bg-slate-50 dark:hover:border-white/10 dark:hover:bg-white/5'}"
				on:click={() => handleSwitchContext(ctx.id)}
			>
				<div class="flex items-center gap-2">
					<span class="truncate text-xs font-bold text-slate-900 dark:text-slate-100">
						{ctx.firstMessage || 'New conversation'}
					</span>
					<div
						role="button"
						tabindex="0"
						class="ml-auto flex size-5 cursor-pointer items-center justify-center rounded transition-colors duration-100 hover:bg-slate-200 dark:hover:bg-white/15 md:hidden group-hover:flex"
						on:click={(e) => handleClearContext(e, ctx.id)}
						on:keydown={(e) => e.key === 'Enter' && handleClearContext(e, ctx.id)}
						title="Clear context"
					>
						<span class="text-sm leading-none text-slate-500 hover:text-slate-800 dark:text-slate-300 dark:hover:text-white">×</span>
					</div>
				</div>
				<div class="flex items-center gap-2 text-[10px] font-medium text-slate-500 dark:text-slate-400/80">
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
