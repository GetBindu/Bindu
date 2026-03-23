<script lang="ts">
	import type { Message } from "$lib/types/Message";
	import IconInfo from "~icons/lucide/info";
	import IconX from "~icons/lucide/x";
	import IconMessageSquare from "~icons/lucide/message-square";
	import IconCornerDownRight from "~icons/lucide/corner-down-right";
	import FeedbackModal from "./FeedbackModal.svelte";
	import { submitTaskFeedback } from "$lib/utils/agentMessageHandler";

	let {
		message,
		onReply
	}: {
		message: Message;
		onReply?: (taskId: string) => void;
	} = $props();
	let showInfo = $state(false);
	let showFeedbackModal = $state(false);

	const taskMetadata = $derived(message.taskMetadata);
	const hasTaskInfo = $derived(!!taskMetadata);

	function getStatusColor(status: string): string {
		switch (status) {
			case 'completed':
				return 'text-green-600 dark:text-green-400';
			case 'working':
			case 'submitted':
				return 'text-blue-600 dark:text-blue-400';
			case 'input-required':
				return 'text-yellow-600 dark:text-yellow-400';
			case 'failed':
			case 'canceled':
				return 'text-red-600 dark:text-red-400';
			default:
				return 'text-gray-600 dark:text-gray-400';
		}
	}

	function getStatusLabel(status: string): string {
		return status.split('-').map(word =>
			word.charAt(0).toUpperCase() + word.slice(1)
		).join(' ');
	}

	function truncateId(id: string): string {
		if (id.length <= 12) return id;
		return `${id.slice(0, 6)}...${id.slice(-6)}`;
	}

	async function handleFeedbackSubmit(feedback: string, rating: number) {
		if (!taskMetadata) return;
		await submitTaskFeedback(taskMetadata.taskId, feedback, rating);
	}
</script>

{#if hasTaskInfo}
	<div class="relative inline-block">
		<button
			onclick={() => showInfo = !showInfo}
			class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
			title="Task Information"
			aria-label="Show task information"
		>
			<IconInfo class="size-4 text-gray-500 dark:text-gray-400" />
		</button>

		{#if showInfo}
			<div
				class="absolute right-0 top-full mt-2 z-50 w-80 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4"
			>
				<div class="flex items-center justify-between mb-3">
					<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
						Task Information
					</h3>
					<button
						onclick={() => showInfo = false}
						class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						aria-label="Close"
					>
						<IconX class="size-4 text-gray-500 dark:text-gray-400" />
					</button>
				</div>

				<div class="space-y-3 text-sm">
					{#if taskMetadata}
						<div>
							<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
								Status
							</div>
							<div class="font-medium {getStatusColor(taskMetadata.status)}">
								{getStatusLabel(taskMetadata.status)}
							</div>
						</div>

						<div>
							<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
								Task ID
							</div>
							<div class="font-mono text-xs text-gray-700 dark:text-gray-300 break-all">
								{taskMetadata.taskId}
							</div>
							<button
								onclick={() => navigator.clipboard.writeText(taskMetadata!.taskId)}
								class="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
							>
								Copy
							</button>
						</div>

						<div>
							<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
								Context ID
							</div>
							<div class="font-mono text-xs text-gray-700 dark:text-gray-300 break-all">
								{taskMetadata.contextId}
							</div>
							<button
								onclick={() => navigator.clipboard.writeText(taskMetadata!.contextId)}
								class="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
							>
								Copy
							</button>
						</div>

						<!-- Reference Tasks -->
						{#if taskMetadata.referenceTaskIds?.length}
							<div class="pt-3 border-t border-gray-200 dark:border-gray-700">
								<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
									References
								</div>
								<div class="space-y-1">
									{#each taskMetadata.referenceTaskIds as refId}
										<div class="flex items-center gap-2">
											<span class="text-gray-500 dark:text-gray-400">↳</span>
											<span class="font-mono text-xs text-gray-700 dark:text-gray-300">
												{refId.substring(0, 8)}...
											</span>
											<button
												onclick={() => navigator.clipboard.writeText(refId)}
												class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
												title="Copy full task ID"
											>
												Copy
											</button>
										</div>
									{/each}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
									Tasks this message continues from
								</div>
							</div>
						{/if}

						<!-- Actions -->
						<div class="pt-3 border-t border-gray-200 dark:border-gray-700 space-y-2">
							<!-- Reply Button -->
							{#if onReply}
								<button
									onclick={() => {
										showInfo = false;
										onReply?.(taskMetadata!.taskId);
									}}
									class="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
								>
									<IconCornerDownRight class="size-4" />
									Reply to This Task
								</button>
							{/if}

							<!-- Feedback Button -->
							<button
								onclick={() => {
									showInfo = false;
									showFeedbackModal = true;
								}}
								class="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
							>
								<IconMessageSquare class="size-4" />
								Submit Feedback
							</button>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}

{#if showFeedbackModal && taskMetadata}
	<FeedbackModal
		taskId={taskMetadata.taskId}
		onClose={() => showFeedbackModal = false}
		onSubmit={handleFeedbackSubmit}
	/>
{/if}
