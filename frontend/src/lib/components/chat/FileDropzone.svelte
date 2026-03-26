<script lang="ts">
	import { requireAuthUser } from "$lib/utils/auth";
	import { validateFiles, getFileUploadConstraints } from "$lib/utils/fileValidation";
	import CarbonImage from "~icons/carbon/image";
	import CarbonWarningAltFilled from "~icons/carbon/warning-alt-filled";

	interface Props {
		files: File[];
		mimeTypes?: string[];
		onDrag?: boolean;
		onDragInner?: boolean;
		onError?: (error: string) => void;
	}

	let {
		files = $bindable(),
		mimeTypes = [],
		onDrag = $bindable(false),
		onDragInner = $bindable(false),
		onError,
	}: Props = $props();

	let errorMessage = $state<string | null>(null);
	let errorTimeout: ReturnType<typeof setTimeout> | undefined;

	async function dropHandle(event: DragEvent) {
		event.preventDefault();
		errorMessage = null;

		if (requireAuthUser()) {
			showError("Please authenticate to upload files");
			return;
		}

		if (!event.dataTransfer?.items) return;

		// Extract files from drag event
		const droppedFiles: File[] = [];
		for (let i = 0; i < event.dataTransfer.items.length; i++) {
			const file = event.dataTransfer.items[i].getAsFile();
			if (file) {
				droppedFiles.push(file);
			}
		}

		// Validate files
		if (droppedFiles.length > 0) {
			const { valid, errors } = validateFiles(droppedFiles, mimeTypes);

			if (errors.length > 0) {
				const errorMsg = errors.join("\n");
				showError(errorMsg);
				onError?.(errorMsg);
			}

			if (valid.length > 0) {
				files = [...files, ...valid];
			}
		}

		onDrag = false;
		onDragInner = false;
	}

	function showError(message: string) {
		errorMessage = message;
		if (errorTimeout) clearTimeout(errorTimeout);
		errorTimeout = setTimeout(() => {
			errorMessage = null;
		}, 6000);
	}
</script>

<div class="w-full max-w-4xl space-y-2">
	{#if errorMessage}
		<div
			class="flex gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-900/30 dark:text-red-200"
			role="alert"
		>
			<CarbonWarningAltFilled class="h-5 w-5 flex-shrink-0 pt-0.5" />
			<div>
				<p class="font-medium">Upload error</p>
				<p class="mt-1 whitespace-pre-wrap text-xs">{errorMessage}</p>
			</div>
		</div>
	{/if}

	<div
		id="dropzone"
		role="form"
		ondrop={dropHandle}
		ondragenter={() => (onDragInner = true)}
		ondragleave={() => (onDragInner = false)}
		ondragover={(e) => {
			e.preventDefault();
		}}
		class="relative flex h-28 flex-col items-center justify-center gap-1 rounded-xl border-2 border-dotted transition-colors {onDragInner
			? 'border-blue-200 !bg-blue-600/10 text-blue-600 *:pointer-events-none dark:border-blue-600 dark:bg-blue-600/20 dark:text-blue-600'
			: 'border-gray-300 bg-gray-50 text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400'}"
	>
		<CarbonImage class="text-xl" />
		<p class="font-medium">Drop files here to upload</p>
		<p class="text-xs opacity-75">or use the attachment button below</p>
	</div>

	{#if mimeTypes.length > 0}
		<p class="text-xs text-gray-600 dark:text-gray-400">
			{getFileUploadConstraints(mimeTypes)}
		</p>
	{/if}
</div>
