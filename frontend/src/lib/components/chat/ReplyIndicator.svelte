<script lang="ts">
	import IconX from "~icons/lucide/x";
	import IconCornerDownRight from "~icons/lucide/corner-down-right";

	let {
		taskId,
		onClear
	}: {
		taskId: string;
		onClear: () => void;
	} = $props();

	function truncateId(id: string): string {
		return id.substring(0, 8);
	}
</script>

<div class="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
	<IconCornerDownRight class="size-4 text-blue-600 dark:text-blue-400 flex-shrink-0" />
	<span class="text-sm text-blue-700 dark:text-blue-300">
		Replying to task: <span class="font-mono">{truncateId(taskId)}...</span>
	</span>
	<button
		onclick={onClear}
		class="ml-auto p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors"
		title="Cancel reply"
		aria-label="Cancel reply"
	>
		<IconX class="size-4 text-blue-600 dark:text-blue-400" />
	</button>
</div>
