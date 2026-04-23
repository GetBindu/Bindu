<script lang="ts">
	import { onMount, tick } from "svelte";

	import { afterNavigate } from "$app/navigation";

	import { DropdownMenu } from "bits-ui";
	import IconPlus from "~icons/lucide/plus";
	import CarbonImage from "~icons/carbon/image";
	import CarbonDocument from "~icons/carbon/document";
	import CarbonUpload from "~icons/carbon/upload";
	import CarbonLink from "~icons/carbon/link";
	import CarbonChevronRight from "~icons/carbon/chevron-right";
	import CarbonClose from "~icons/carbon/close";
	import UrlFetchModal from "./UrlFetchModal.svelte";
	import { TEXT_MIME_ALLOWLIST, IMAGE_MIME_ALLOWLIST_DEFAULT } from "$lib/constants/mime";

	import { isVirtualKeyboard } from "$lib/utils/isVirtualKeyboard";
	import { requireAuthUser } from "$lib/utils/auth";
	import { page } from "$app/state";

	interface Props {
		files?: File[];
		mimeTypes?: string[];
		value?: string;
		placeholder?: string;
		loading?: boolean;
		disabled?: boolean;
		// tools removed
		modelIsMultimodal?: boolean;
		// Whether the currently selected model supports tool calling (incl. overrides)
		modelSupportsTools?: boolean;
		children?: import("svelte").Snippet;
		onPaste?: (e: ClipboardEvent) => void;
		focused?: boolean;
		onsubmit?: () => void;
	}

	let {
		files = $bindable([]),
		mimeTypes = [],
		value = $bindable(""),
		placeholder = "",
		loading = false,
		disabled = false,

		modelIsMultimodal = false,
		modelSupportsTools = true,
		children,
		onPaste,
		focused = $bindable(false),
		onsubmit,
	}: Props = $props();

	const onFileChange = async (e: Event) => {
		if (!e.target) return;
		const target = e.target as HTMLInputElement;
		const selected = Array.from(target.files ?? []);
		if (selected.length === 0) return;
		files = [...files, ...selected];
		await tick();
		void focusTextarea();
	};

	let textareaElement: HTMLTextAreaElement | undefined = $state();
	let isCompositionOn = $state(false);
	let blurTimeout: ReturnType<typeof setTimeout> | null = $state(null);

	let fileInputEl: HTMLInputElement | undefined = $state();
	let isUrlModalOpen = $state(false);
	let isDropdownOpen = $state(false);

	function openPickerWithAccept(accept: string) {
		if (!fileInputEl) return;
		const allAccept = mimeTypes.join(",");
		fileInputEl.setAttribute("accept", accept);
		fileInputEl.click();
		queueMicrotask(() => fileInputEl?.setAttribute("accept", allAccept));
	}

	function openFilePickerText() {
		const textAccept =
			mimeTypes.filter((m) => !(m === "image/*" || m.startsWith("image/"))).join(",") ||
			TEXT_MIME_ALLOWLIST.join(",");
		openPickerWithAccept(textAccept);
	}

	function openFilePickerImage() {
		const imageAccept =
			mimeTypes.filter((m) => m === "image/*" || m.startsWith("image/")).join(",") ||
			IMAGE_MIME_ALLOWLIST_DEFAULT.join(",");
		openPickerWithAccept(imageAccept);
	}

	const waitForAnimationFrame = () =>
		typeof requestAnimationFrame === "function"
			? new Promise<void>((resolve) => {
					requestAnimationFrame(() => resolve());
				})
			: Promise.resolve();

	async function focusTextarea() {
		if (page.data.shared && page.data.loginEnabled && !page.data.user) return;
		if (!textareaElement || textareaElement.disabled || isVirtualKeyboard()) return;
		if (typeof document !== "undefined" && document.activeElement === textareaElement) return;

		await tick();

		if (typeof requestAnimationFrame === "function") {
			await waitForAnimationFrame();
			await waitForAnimationFrame();
		}

		if (!textareaElement || textareaElement.disabled || isVirtualKeyboard()) return;

		try {
			textareaElement.focus({ preventScroll: true });
		} catch {
			textareaElement.focus();
		}
	}

	function handleFetchedFiles(newFiles: File[]) {
		if (!newFiles?.length) return;
		files = [...files, ...newFiles];
		queueMicrotask(async () => {
			await tick();
			void focusTextarea();
		});
	}

	onMount(() => {
		void focusTextarea();
	});

	afterNavigate(() => {
		void focusTextarea();
	});

	function adjustTextareaHeight() {
		if (!textareaElement) {
			return;
		}

		textareaElement.style.height = "auto";
		textareaElement.style.height = `${textareaElement.scrollHeight}px`;

		if (textareaElement.selectionStart === textareaElement.value.length) {
			textareaElement.scrollTop = textareaElement.scrollHeight;
		}
	}

	$effect(() => {
		if (!textareaElement) return;
		void value;
		adjustTextareaHeight();
	});

	function handleKeydown(event: KeyboardEvent) {
		if (
			event.key === "Enter" &&
			!event.shiftKey &&
			!isCompositionOn &&
			!isVirtualKeyboard() &&
			value.trim() !== ""
		) {
			event.preventDefault();
			tick();
			onsubmit?.();
		}
	}

	function handleFocus() {
		if (requireAuthUser()) {
			return;
		}
		if (blurTimeout) {
			clearTimeout(blurTimeout);
			blurTimeout = null;
		}
		focused = true;
	}

	function handleBlur() {
		if (!isVirtualKeyboard()) {
			focused = false;
			return;
		}

		if (blurTimeout) {
			clearTimeout(blurTimeout);
		}

		blurTimeout = setTimeout(() => {
			blurTimeout = null;
			focused = false;
		});
	}

	// Show file upload when any mime is allowed (text always; images if multimodal)
	let showFileUpload = $derived(mimeTypes.length > 0);
	let showNoTools = $derived(!showFileUpload);
</script>

<div class="flex w-full flex-col gap-[12px]" onpaste={onPaste}>
	<textarea
		rows="1"
		tabindex="0"
		inputmode="text"
		class="chat-input scrollbar-custom max-h-[6lh] w-full resize-none overflow-y-auto overflow-x-hidden border-0 bg-transparent p-0 outline-none focus:ring-0 focus-visible:ring-0"

		class:text-gray-400={disabled}
		bind:value
		bind:this={textareaElement}
		onkeydown={handleKeydown}
		oncompositionstart={() => (isCompositionOn = true)}
		oncompositionend={() => (isCompositionOn = false)}
		{placeholder}
		{disabled}
		onfocus={handleFocus}
		onblur={handleBlur}
		onbeforeinput={requireAuthUser}
	></textarea>

	{#if !showNoTools || children}
		<div class="flex w-full items-center gap-[6px]">
			{#if showFileUpload && !showNoTools}
				<input
					bind:this={fileInputEl}
					disabled={loading}
					class="absolute hidden size-0"
					aria-label="Upload file"
					type="file"
					multiple
					onchange={onFileChange}
					onclick={(e) => {
						if (requireAuthUser()) {
							e.preventDefault();
						}
					}}
					accept={mimeTypes.join(",")}
				/>

				<DropdownMenu.Root
					bind:open={isDropdownOpen}
					onOpenChange={(open) => {
						if (open && requireAuthUser()) {
							isDropdownOpen = false;
							return;
						}
						isDropdownOpen = open;
					}}
				>
					<DropdownMenu.Trigger
						class="composer-btn icon-btn"
						disabled={loading}
						aria-label="Add attachment"
					>
						<IconPlus class="size-3.5" />
					</DropdownMenu.Trigger>
					<DropdownMenu.Portal>
						<DropdownMenu.Content
							class="z-50 rounded-xl border border-gray-200 bg-white p-1 text-gray-800 shadow-lg backdrop-blur dark:border-white/10 dark:bg-[#0d0f14]/95 dark:text-gray-200"
							side="top"
							sideOffset={8}
							align="start"
							trapFocus={false}
							onCloseAutoFocus={(e) => e.preventDefault()}
							interactOutsideBehavior="defer-otherwise-close"
						>
							{#if modelIsMultimodal}
								<DropdownMenu.Item
									class="flex h-9 select-none items-center gap-1 rounded-md px-2 text-sm text-slate-700 transition-colors data-[highlighted]:bg-slate-100 focus-visible:outline-none dark:text-gray-300 dark:data-[highlighted]:bg-white/10 sm:h-8"
									onSelect={() => openFilePickerImage()}
								>
									<CarbonImage class="size-4 opacity-80" />
									Add image(s)
								</DropdownMenu.Item>
							{/if}

							<DropdownMenu.Sub>
								<DropdownMenu.SubTrigger
									class="flex h-9 select-none items-center gap-1 rounded-md px-2 text-sm text-slate-700 transition-colors data-[highlighted]:bg-slate-100 data-[state=open]:bg-slate-100 focus-visible:outline-none dark:text-gray-300 dark:data-[highlighted]:bg-white/10 dark:data-[state=open]:bg-white/10 sm:h-8"
								>
									<div class="flex items-center gap-1">
										<CarbonDocument class="size-4 opacity-80" />
										Add text file
									</div>
									<div class="ml-auto flex items-center">
										<CarbonChevronRight class="size-4 opacity-70" />
									</div>
								</DropdownMenu.SubTrigger>
								<DropdownMenu.SubContent
									class="z-50 rounded-xl border border-gray-200 bg-white p-1 text-gray-800 shadow-lg backdrop-blur dark:border-white/10 dark:bg-[#0d0f14]/95 dark:text-gray-200"
									sideOffset={10}
									trapFocus={false}
									onCloseAutoFocus={(e) => e.preventDefault()}
									interactOutsideBehavior="defer-otherwise-close"
								>
									<DropdownMenu.Item
										class="flex h-9 select-none items-center gap-1 rounded-md px-2 text-sm text-slate-700 transition-colors data-[highlighted]:bg-slate-100 focus-visible:outline-none dark:text-gray-300 dark:data-[highlighted]:bg-white/10 sm:h-8"
										onSelect={() => openFilePickerText()}
									>
										<CarbonUpload class="size-4 opacity-80" />
										Upload from device
									</DropdownMenu.Item>
									<DropdownMenu.Item
										class="flex h-9 select-none items-center gap-1 rounded-md px-2 text-sm text-slate-700 transition-colors data-[highlighted]:bg-slate-100 focus-visible:outline-none dark:text-gray-300 dark:data-[highlighted]:bg-white/10 sm:h-8"
										onSelect={() => (isUrlModalOpen = true)}
									>
										<CarbonLink class="size-4 opacity-80" />
										Fetch from URL
									</DropdownMenu.Item>
								</DropdownMenu.SubContent>
							</DropdownMenu.Sub>
						</DropdownMenu.Content>
					</DropdownMenu.Portal>
				</DropdownMenu.Root>
			{/if}

			<!-- right side buttons (voice, send etc.) pushed to far right -->
			<div class="ml-auto flex items-center gap-[6px]">
				{@render children?.()}
			</div>
		</div>
	{/if}

	<UrlFetchModal

		bind:open={isUrlModalOpen}
		acceptMimeTypes={mimeTypes}
		onfiles={handleFetchedFiles}
	/>
</div>


<style lang="postcss">
	/* Allow pre to inherit font but NOT textarea — composer overrides it */
	:global(pre) {
		font-family: inherit;
		box-sizing: border-box;
		line-height: 1.5;
		font-size: 15px;
	}

	/* textarea base reset only */
	:global(textarea) {
		box-sizing: border-box;
	}

	/* Chat input text */
	.chat-input {
		color: var(--text);
		font-size: 15px;
		line-height: 1.5;
	}

	.chat-input::placeholder {
		color: var(--placeholder);
	}
</style>
