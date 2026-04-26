<script lang="ts">
	import IconPhone from "~icons/lucide/phone";

	interface Props {
		disabled?: boolean;
		active?: boolean;
		onclick?: () => void;
	}

	let { disabled = false, active = false, onclick }: Props = $props();
</script>

<button
	type="button"
	class="btn absolute bottom-2 right-[4.5rem] mr-1.5 size-8 self-end rounded-full border transition-none sm:size-7 {active
		 ? 'border-transparent bg-green-600 text-white hover:bg-green-500'
		 : 'border bg-white/50 text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:border-transparent dark:bg-gray-600/50 dark:text-gray-300 dark:hover:bg-gray-500 dark:hover:text-white'} {disabled ? 'opacity-50 cursor-not-allowed' : ''}"
	{disabled}
	onclick={() => onclick?.()}
	aria-label={active ? "End voice call" : "Start voice call"}
>
	<IconPhone class="size-4" />
</button>
