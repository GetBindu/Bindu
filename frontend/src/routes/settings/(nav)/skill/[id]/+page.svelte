<script lang="ts">
	import { page } from "$app/state";

	interface DetailedSkill {
		id: string;
		name: string;
		description: string;
		version: string;
		author?: string;
		tags: string[];
		input_modes: string[];
		output_modes: string[];
		examples: string[];
		capabilities_detail?: Record<string, any>;
		requirements?: {
			packages?: string[];
			system?: string[];
			min_memory_mb?: number;
		};
		performance?: {
			avg_processing_time_ms?: number;
			max_concurrent_requests?: number;
			memory_per_request_mb?: number;
			scalability?: string;
		};
		allowed_tools?: string[];
		documentation?: {
			overview?: string;
			use_cases?: {
				when_to_use?: string[];
				when_not_to_use?: string[];
			};
			input_structure?: string;
			output_format?: string;
			quality_guidelines?: string[];
			error_handling?: string[];
			examples?: Array<{
				title: string;
				input: any;
				output: any;
			}>;
			best_practices?: {
				for_developers?: string[];
				for_orchestrators?: string[];
			};
		};
		assessment?: {
			keywords?: string[];
			specializations?: Array<{
				domain: string;
				confidence_boost: number;
			}>;
			anti_patterns?: string[];
			complexity_indicators?: Record<string, string[]>;
		};
		documentation_path?: string;
		has_documentation?: boolean;
	}

	let skill = $state<DetailedSkill | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Reactive effect that runs whenever page.params.id changes
	$effect(() => {
		const skillId = page.params.id;

		// Reset state when skill ID changes
		loading = true;
		error = null;
		skill = null;

		fetch(`/api/agent-skills/${skillId}`)
			.then((res) => {
				if (res.ok) {
					return res.json();
				} else {
					error = "Could not load skill details";
					return null;
				}
			})
			.then((data) => {
				if (data) {
					skill = data;
				}
			})
			.catch(() => {
				error = "Failed to fetch skill information";
			})
			.finally(() => {
				loading = false;
			});
	});
</script>

<div class="flex flex-col gap-6">
	{#if loading}
		<div class="flex items-center gap-2 text-gray-500">
			<span class="size-2 animate-pulse rounded-full bg-gray-400"></span>
			Loading skill details...
		</div>
	{:else if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
			<p class="text-sm text-red-600 dark:text-red-400">{error}</p>
		</div>
	{:else if skill}
		<!-- Skill Header -->
		<div
			class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<div class="flex items-start justify-between">
				<div class="flex-1">
					<div class="flex items-center gap-2">
						<span
							class="rounded bg-green-100 px-2 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
						>
							skill
						</span>
						<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
							{skill.name}
						</h1>
						<span
							class="rounded bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
						>
							v{skill.version}
						</span>
					</div>
					<p class="mt-1 font-mono text-xs text-gray-500 dark:text-gray-400">{skill.id}</p>
					{#if skill.author}
						<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
							Author: <span class="font-medium">{skill.author}</span>
						</p>
					{/if}
				</div>
			</div>

			{#if skill.tags && skill.tags.length > 0}
				<div class="mt-4 flex flex-wrap gap-2">
					{#each skill.tags as tag}
						<span
							class="rounded-full bg-gray-200 px-3 py-1 text-xs text-gray-700 dark:bg-gray-600 dark:text-gray-300"
						>
							#{tag}
						</span>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Description -->
		<div
			class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Description</h2>
			<p class="whitespace-pre-line text-sm leading-relaxed text-gray-600 dark:text-gray-400">
				{skill.description}
			</p>
		</div>

		<!-- Overview -->
		{#if skill.documentation?.overview}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Overview</h2>
				<p class="whitespace-pre-line text-sm leading-relaxed text-gray-600 dark:text-gray-400">
					{skill.documentation.overview}
				</p>
			</div>
		{/if}

		<!-- Examples -->
		{#if skill.examples && skill.examples.length > 0}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Example Queries
				</h2>
				<ul class="space-y-2">
					{#each skill.examples as example}
						<li
							class="rounded-lg bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-700/50 dark:text-gray-300"
						>
							"{example}"
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Use Cases -->
		{#if skill.documentation?.use_cases}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Use Cases</h2>
				<div class="grid gap-4 md:grid-cols-2">
					{#if skill.documentation.use_cases.when_to_use}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-green-700 dark:text-green-400">
								✓ When to Use
							</h3>
							<ul class="space-y-1">
								{#each skill.documentation.use_cases.when_to_use as useCase}
									<li class="text-sm text-gray-600 dark:text-gray-400 before:mr-2 before:content-['•']">
										{useCase}
									</li>
								{/each}
							</ul>
						</div>
					{/if}
					{#if skill.documentation.use_cases.when_not_to_use}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-red-700 dark:text-red-400">
								✗ When Not to Use
							</h3>
							<ul class="space-y-1">
								{#each skill.documentation.use_cases.when_not_to_use as useCase}
									<li class="text-sm text-gray-600 dark:text-gray-400 before:mr-2 before:content-['•']">
										{useCase}
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Input/Output Modes -->
		<div
			class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
				Input/Output Modes
			</h2>
			<div class="grid gap-4 md:grid-cols-2">
				<div>
					<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
						Input Modes
					</h3>
					<div class="flex flex-wrap gap-2">
						{#each skill.input_modes as mode}
							<span
								class="rounded bg-green-100 px-3 py-1 font-mono text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400"
							>
								{mode}
							</span>
						{/each}
					</div>
				</div>
				<div>
					<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
						Output Modes
					</h3>
					<div class="flex flex-wrap gap-2">
						{#each skill.output_modes as mode}
							<span
								class="rounded bg-purple-100 px-3 py-1 font-mono text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
							>
								{mode}
							</span>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- Input/Output Structure -->
		{#if skill.documentation?.input_structure || skill.documentation?.output_format}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Input/Output Structure
				</h2>
				<div class="space-y-4">
					{#if skill.documentation.input_structure}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
								Input Structure
							</h3>
							<pre
								class="overflow-x-auto rounded-lg bg-gray-50 p-4 font-mono text-xs text-gray-800 dark:bg-gray-900 dark:text-gray-300">{skill.documentation.input_structure}</pre>
						</div>
					{/if}
					{#if skill.documentation.output_format}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
								Output Format
							</h3>
							<pre
								class="overflow-x-auto rounded-lg bg-gray-50 p-4 font-mono text-xs text-gray-800 dark:bg-gray-900 dark:text-gray-300">{skill.documentation.output_format}</pre>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Capabilities Detail -->
		{#if skill.capabilities_detail}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Detailed Capabilities
				</h2>
				<div class="space-y-3">
					{#each Object.entries(skill.capabilities_detail) as [key, value]}
						<div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700/50">
							<h3 class="mb-2 font-medium capitalize text-gray-900 dark:text-white">
								{key.replace(/_/g, ' ')}
							</h3>
							<pre
								class="overflow-x-auto font-mono text-xs text-gray-600 dark:text-gray-400">{JSON.stringify(value, null, 2)}</pre>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Performance Metrics -->
		{#if skill.performance}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Performance Metrics
				</h2>
				<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
					{#if skill.performance.avg_processing_time_ms}
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400">Average Processing Time</p>
							<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
								{skill.performance.avg_processing_time_ms}ms
							</p>
						</div>
					{/if}
					{#if skill.performance.max_concurrent_requests}
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400">Max Concurrent Requests</p>
							<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
								{skill.performance.max_concurrent_requests}
							</p>
						</div>
					{/if}
					{#if skill.performance.memory_per_request_mb}
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400">Memory per Request</p>
							<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-gray-100">
								{skill.performance.memory_per_request_mb}MB
							</p>
						</div>
					{/if}
					{#if skill.performance.scalability}
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400">Scalability</p>
							<p class="mt-1 text-lg font-semibold capitalize text-gray-900 dark:text-gray-100">
								{skill.performance.scalability}
							</p>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Requirements -->
		{#if skill.requirements}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Requirements</h2>
				<div class="grid gap-4 md:grid-cols-3">
					{#if skill.requirements.min_memory_mb}
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400">Minimum Memory</p>
							<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
								{skill.requirements.min_memory_mb}MB
							</p>
						</div>
					{/if}
					{#if skill.requirements.packages && skill.requirements.packages.length > 0}
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400">Package Dependencies</p>
							<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
								{skill.requirements.packages.length} packages
							</p>
						</div>
					{/if}
					{#if skill.requirements.system && skill.requirements.system.length > 0}
						<div>
							<p class="text-xs text-gray-500 dark:text-gray-400">System Dependencies</p>
							<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
								{skill.requirements.system.length} dependencies
							</p>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Allowed Tools -->
		{#if skill.allowed_tools && skill.allowed_tools.length > 0}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Allowed Tools</h2>
				<div class="flex flex-wrap gap-2">
					{#each skill.allowed_tools as tool}
						<span
							class="rounded bg-orange-100 px-3 py-1 text-sm text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
						>
							{tool}
						</span>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Documentation Examples -->
		{#if skill.documentation?.examples && skill.documentation.examples.length > 0}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Detailed Examples
				</h2>
				<div class="space-y-4">
					{#each skill.documentation.examples as example}
						<div class="rounded-lg border border-gray-200 p-4 dark:border-gray-600">
							<h3 class="mb-2 font-semibold text-gray-900 dark:text-white">{example.title}</h3>
							<div class="space-y-2">
								<div>
									<p class="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Input:</p>
									<pre
										class="overflow-x-auto rounded bg-gray-50 p-2 font-mono text-xs text-gray-800 dark:bg-gray-900 dark:text-gray-300">{typeof example.input === 'string' ? example.input : JSON.stringify(example.input, null, 2)}</pre>
								</div>
								<div>
									<p class="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Output:</p>
									<pre
										class="overflow-x-auto rounded bg-gray-50 p-2 font-mono text-xs text-gray-800 dark:bg-gray-900 dark:text-gray-300">{typeof example.output === 'string' ? example.output : JSON.stringify(example.output, null, 2)}</pre>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Quality Guidelines -->
		{#if skill.documentation?.quality_guidelines && skill.documentation.quality_guidelines.length > 0}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Quality Guidelines
				</h2>
				<ul class="space-y-2">
					{#each skill.documentation.quality_guidelines as guideline}
						<li
							class="text-sm text-gray-600 dark:text-gray-400 before:mr-2 before:text-green-600 before:content-['✓'] dark:before:text-green-400"
						>
							{guideline}
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- Best Practices -->
		{#if skill.documentation?.best_practices}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Best Practices</h2>
				<div class="grid gap-4 md:grid-cols-2">
					{#if skill.documentation.best_practices.for_developers}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
								For Developers
							</h3>
							<ul class="space-y-1">
								{#each skill.documentation.best_practices.for_developers as practice}
									<li class="text-sm text-gray-600 dark:text-gray-400 before:mr-2 before:content-['•']">
										{practice}
									</li>
								{/each}
							</ul>
						</div>
					{/if}
					{#if skill.documentation.best_practices.for_orchestrators}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
								For Orchestrators
							</h3>
							<ul class="space-y-1">
								{#each skill.documentation.best_practices.for_orchestrators as practice}
									<li class="text-sm text-gray-600 dark:text-gray-400 before:mr-2 before:content-['•']">
										{practice}
									</li>
								{/each}
							</ul>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Assessment -->
		{#if skill.assessment}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Skill Assessment
				</h2>
				<div class="space-y-4">
					{#if skill.assessment.keywords && skill.assessment.keywords.length > 0}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Keywords</h3>
							<div class="flex flex-wrap gap-1">
								{#each skill.assessment.keywords as keyword}
									<span
										class="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
									>
										{keyword}
									</span>
								{/each}
							</div>
						</div>
					{/if}
					{#if skill.assessment.anti_patterns && skill.assessment.anti_patterns.length > 0}
						<div>
							<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
								Anti-patterns
							</h3>
							<div class="flex flex-wrap gap-1">
								{#each skill.assessment.anti_patterns as pattern}
									<span
										class="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-400"
									>
										{pattern}
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>
