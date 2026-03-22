<script lang="ts">
	import type { VoiceTranscript } from "$lib/stores/voice";

	interface Props {
		items: VoiceTranscript[];
	}

	let { items }: Props = $props();
</script>

<div class="flex max-h-72 flex-col gap-2 overflow-y-auto rounded-lg border border-gray-200 bg-white/80 p-3 text-sm dark:border-gray-700 dark:bg-gray-900/80">
	{#if items.length === 0}
		<p class="text-gray-500">Voice transcript will appear here...</p>
	{:else}
		{#each items as item, idx (idx)}
			<div class="rounded-md px-2 py-1 {item.role === 'user' ? 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100' : 'bg-green-50 text-green-900 dark:bg-green-950/50 dark:text-green-200'}">
				<div class="mb-0.5 text-[11px] uppercase tracking-wide opacity-70">
					{item.role === 'user' ? 'You' : 'Agent'}
				</div>
				<div>{item.text}</div>
			</div>
		{/each}
	{/if}
</div>
