<script lang="ts">
	import type { Model } from "$lib/types/Model";

	interface Props {
		currentModel: Model;
		onmessage?: (content: string) => void;
	}

	let { currentModel: _currentModel, onmessage }: Props = $props();

</script>

<div class="my-auto grid items-center justify-center gap-8 text-center">
	<div class="intro-hero select-none">
		<div class="intro-glow" aria-hidden="true"></div>
		<div class="intro-mark-row flex-col gap-2">
			<h1 class="intro-title rounded-xl text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl lg:text-6xl">
				Chat with Bindu
			</h1>
			<p class="intro-tagline mt-4 text-[11px] font-semibold uppercase tracking-[0.4em] text-slate-500/80 dark:text-slate-400/40">
				IMAGINE • BUILD • CONNECT
			</p>

		</div>


	</div>
</div>

<style>
	.intro-hero {
		position: relative;
		animation: intro-fade-up 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
	}

	@keyframes intro-fade-up {
		from {
			opacity: 0;
			transform: translateY(12px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}


	.intro-glow {
		position: absolute;
		inset: 0;
		margin: auto;
		width: 360px;
		height: 160px;
		border-radius: 9999px;
		background: radial-gradient(ellipse at center, rgba(85, 124, 247, 0.17) 0%, transparent 70%);
		filter: blur(26px);
		pointer-events: none;
	}

	.intro-mark-row {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
	}


	:global(.dark) .intro-glow {
		background: radial-gradient(ellipse at center, rgba(98, 139, 255, 0.24) 0%, transparent 70%);
	}

	.intro-title {
		background: linear-gradient(135deg, #1e293b 0%, #475569 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	:global(.dark) .intro-title {
		background: linear-gradient(180deg, #d9e2f3 0%, #a5afc4 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	@media (max-height: 650px) {
		.intro-title {
			font-size: 1.5rem !important; /* text-2xl equivalent */
			line-height: 2rem !important;
		}
		.intro-glow {
			display: none;
		}
		.intro-tagline {
			margin-top: 0.5rem;
		}
	}

</style>
