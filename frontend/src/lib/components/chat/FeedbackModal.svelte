<script lang="ts">
	import IconX from "~icons/lucide/x";
	import IconSend from "~icons/lucide/send";

	let {
		taskId,
		onClose,
		onSubmit
	}: {
		taskId: string;
		onClose: () => void;
		onSubmit: (feedback: string, rating: number) => Promise<void>;
	} = $props();

	let feedback = $state("");
	let rating = $state(5);
	let submitting = $state(false);
	let error = $state("");
	let success = $state(false);

	async function handleSubmit() {
		if (submitting) return;

		try {
			submitting = true;
			error = "";
			await onSubmit(feedback, rating);

			// Show success message
			success = true;

			// Auto-close after 1.5 seconds
			setTimeout(() => {
				onClose();
			}, 1500);
		} catch (err) {
			error = err instanceof Error ? err.message : "Failed to submit feedback";
		} finally {
			submitting = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === "Escape") {
			onClose();
		} else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
			handleSubmit();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Modal Backdrop -->
<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
	onclick={onClose}
	role="presentation"
>
	<!-- Modal Content -->
	<div
		class="relative w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-900"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => e.key === 'Enter' && e.stopPropagation()}
		role="dialog"
		aria-labelledby="feedback-title"
		aria-modal="true"
		tabindex="-1"
	>
		<!-- Header -->
		<div class="mb-4 flex items-center justify-between">
			<h2 id="feedback-title" class="text-lg font-semibold text-gray-900 dark:text-gray-100">
				Submit Feedback
			</h2>
			<button
				onclick={onClose}
				class="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-800"
				aria-label="Close"
			>
				<IconX class="size-5 text-gray-500 dark:text-gray-400" />
			</button>
		</div>

		<!-- Task ID -->
		<div class="mb-4">
			<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Task ID</div>
			<div class="font-mono text-xs text-gray-700 dark:text-gray-300 break-all bg-gray-50 dark:bg-gray-800 p-2 rounded">
				{taskId}
			</div>
		</div>

		<!-- Rating -->
		<div class="mb-4">
			<label for="rating" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
				Rating
			</label>
			<div class="flex items-center gap-2">
				<input
					id="rating"
					type="range"
					min="1"
					max="5"
					bind:value={rating}
					class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
				/>
				<span class="text-lg font-semibold text-gray-900 dark:text-gray-100 w-8 text-center">
					{rating}
				</span>
			</div>
			<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
				<span>Poor</span>
				<span>Excellent</span>
			</div>
		</div>

		<!-- Feedback Text -->
		<div class="mb-4">
			<label for="feedback" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
				Feedback (optional)
			</label>
			<textarea
				id="feedback"
				bind:value={feedback}
				placeholder="Share your thoughts about this response..."
				rows="4"
				class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
			></textarea>
		</div>

		<!-- Success Message -->
		{#if success}
			<div class="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-800 dark:bg-green-900/20 dark:text-green-400 flex items-center gap-2">
				<svg class="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
				</svg>
				Feedback submitted successfully!
			</div>
		{/if}

		<!-- Error Message -->
		{#if error}
			<div class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400">
				{error}
			</div>
		{/if}

		<!-- Actions -->
		<div class="flex justify-end gap-2">
			<button
				onclick={onClose}
				class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
				disabled={submitting}
			>
				Cancel
			</button>
			<button
				onclick={handleSubmit}
				disabled={submitting}
				class="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{#if submitting}
					<div class="size-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
					Submitting...
				{:else}
					<IconSend class="size-4" />
					Submit
				{/if}
			</button>
		</div>

		<div class="mt-3 text-xs text-gray-500 dark:text-gray-400 text-center">
			Press <kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">Esc</kbd> to close or
			<kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">Cmd/Ctrl+Enter</kbd> to submit
		</div>
	</div>
</div>
