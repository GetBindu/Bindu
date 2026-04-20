<script lang="ts">
	import { base } from "$app/paths";
	import { page } from "$app/state";

	import CarbonTrashCan from "~icons/carbon/trash-can";
	import CarbonEdit from "~icons/carbon/edit";
	import type { ConvSidebar } from "$lib/types/ConvSidebar";

	import EditConversationModal from "$lib/components/EditConversationModal.svelte";
	import DeleteConversationModal from "$lib/components/DeleteConversationModal.svelte";
	import { requireAuthUser } from "$lib/utils/auth";

	interface Props {
		conv: ConvSidebar;
		readOnly?: true;
		ondeleteConversation?: (id: string) => void;
		oneditConversationTitle?: (payload: { id: string; title: string }) => void;
	}

	let { conv, readOnly, ondeleteConversation, oneditConversationTitle }: Props = $props();

	let deleteOpen = $state(false);
	let renameOpen = $state(false);
</script>

<a
	data-sveltekit-noscroll
	data-sveltekit-preload-data="tap"
	href="{base}/conversation/{conv.id}"
	class="group flex h-[2.15rem] flex-none items-center gap-1.5 rounded-lg pl-2.5 pr-2 text-slate-600 transition-all duration-150 hover:bg-white hover:text-slate-900 hover:shadow-sm dark:text-gray-300 dark:hover:bg-gray-700/60 dark:hover:text-gray-100 max-sm:h-10
		{conv.id === page.params.id ? 'bg-white font-semibold text-slate-950 shadow-sm ring-1 ring-slate-200 dark:bg-gray-700/80 dark:text-white dark:ring-gray-600/50' : ''}"
>
	<div class="my-2 min-w-0 flex-1 truncate first-letter:uppercase">
		<span>{conv.title}</span>
	</div>

	{#if !readOnly}
		<button
			type="button"
			class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 hover:text-gray-600 dark:hover:text-gray-200 md:hidden md:group-hover:flex"
			title="Edit conversation title"
			onclick={(e) => {
				e.preventDefault();
				if (requireAuthUser()) return;
				renameOpen = true;
			}}
		>
			<CarbonEdit class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" />
		</button>

		<button
			type="button"
			class="flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 hover:text-red-500 md:hidden md:group-hover:flex"
			title="Delete conversation"
			onclick={(event) => {
				event.preventDefault();
				if (requireAuthUser()) return;
				if (event.shiftKey) {
					ondeleteConversation?.(conv.id.toString());
				} else {
					deleteOpen = true;
				}
			}}
		>
			<CarbonTrashCan class="text-xs text-gray-400 hover:text-red-500" />
		</button>
	{/if}
</a>

<!-- Edit title modal -->
{#if renameOpen}
	<EditConversationModal
		open={renameOpen}
		title={conv.title}
		onclose={() => (renameOpen = false)}
		onsave={(payload) => {
			renameOpen = false;
			oneditConversationTitle?.({ id: conv.id.toString(), title: payload.title });
		}}
	/>
{/if}

<!-- Delete confirmation modal -->
{#if deleteOpen}
	<DeleteConversationModal
		open={deleteOpen}
		title={conv.title}
		onclose={() => (deleteOpen = false)}
		ondelete={() => {
			deleteOpen = false;
			ondeleteConversation?.(conv.id.toString());
		}}
	/>
{/if}
