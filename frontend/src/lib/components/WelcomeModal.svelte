<script lang="ts">
	import Modal from "$lib/components/Modal.svelte";
	import { usePublicConfig } from "$lib/utils/PublicConfig.svelte";

	const publicConfig = usePublicConfig();

	interface Props {
		close: () => void;
	}

	let { close }: Props = $props();
</script>

<Modal closeOnBackdrop={false} onclose={close} width="!max-w-[420px] !m-4">
	<div
		class="flex w-full flex-col gap-6 bg-white bg-gradient-to-b to-transparent px-6 py-7 dark:bg-black dark:from-white/10 dark:to-white/5"
	>
		<div>
			<h2 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">
				Welcome to {publicConfig.PUBLIC_APP_NAME}
			</h2>
			<p class="mt-1 text-sm font-medium tracking-wide text-gray-500 dark:text-gray-400">
				Imagine · Build · Connect
			</p>
		</div>

		<div class="text-gray-700 dark:text-gray-200">
			<p class="text-[15px] leading-relaxed">
				Bindu can transform any agent into a microservice that can communicate with other agents.
			</p>
			<p class="mt-3 text-[15px] leading-relaxed">
				Build powerful multi-agent systems where each agent operates as an independent service, seamlessly collaborating to solve complex tasks.
			</p>
		</div>

		<button
			class="w-full rounded-xl bg-black px-5 py-2.5 text-base font-medium text-white hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
			onclick={close}
		>
			Let Bindu Fly 🕊️
		</button>
	</div>
</Modal>
