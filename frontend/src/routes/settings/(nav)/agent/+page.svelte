<script lang="ts">
	import { onMount } from "svelte";

	interface AgentCard {
		id: string;
		name: string;
		description: string;
		url: string;
		version: string;
		protocolVersion: string;
		skills: Array<{
			id: string;
			name: string;
			documentationPath: string;
		}>;
		capabilities: {
			extensions?: Array<{
				uri: string;
				description: string;
				required: boolean;
				params?: Record<string, any>;
			}>;
			pushNotifications?: boolean;
			streaming?: boolean;
		};
		kind: string;
		numHistorySessions: number;
		extraData?: Record<string, any>;
		debugMode: boolean;
		debugLevel: number;
		monitoring: boolean;
		telemetry: boolean;
		agentTrust?: {
			identityProvider?: string;
			inheritedRoles?: string[];
			creatorId?: string;
			creationTimestamp?: number;
			trustVerificationRequired?: boolean;
			allowedOperations?: Record<string, any>;
		};
		defaultInputModes?: string[];
		defaultOutputModes?: string[];
	}

	interface HealthStatus {
		status: string;
		uptime_seconds: number;
		version: string;
		ready: boolean;
	}

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
		requirements?: Record<string, any>;
		performance?: Record<string, any>;
		allowed_tools?: string[];
		documentation?: Record<string, any>;
		assessment?: Record<string, any>;
		documentation_path?: string;
		has_documentation?: boolean;
	}

	interface SkillsResponse {
		skills: DetailedSkill[];
		total: number;
	}

	let agentData = $state<AgentCard | null>(null);
	let healthData = $state<HealthStatus | null>(null);
	let detailedSkills = $state<DetailedSkill[]>([]);
	let rawAgentJson = $state<string>("");
	let agentLoading = $state(true);
	let agentError = $state<string | null>(null);
	let showRawJson = $state(false);
	let expandedSkills = $state<Set<string>>(new Set());
	let jsonCopied = $state(false);

	onMount(async () => {
		try {
			const [cardRes, healthRes, skillsRes] = await Promise.all([
				fetch("/api/agent-card"),
				fetch("/api/agent-health"),
				fetch("/api/agent-skills")
			]);

			if (cardRes.ok) {
				const data = await cardRes.json();
				agentData = data;
				rawAgentJson = JSON.stringify(data, null, 2);
			} else {
				agentError = "Could not load agent info";
			}

			if (healthRes.ok) {
				const data = await healthRes.json();
				healthData = data;
			}

			if (skillsRes.ok) {
				const data: SkillsResponse = await skillsRes.json();
				detailedSkills = data.skills || [];
			}
		} catch (e) {
			agentError = "Agent not connected";
		} finally {
			agentLoading = false;
		}
	});

	function toggleSkillExpansion(skillId: string) {
		const newExpanded = new Set(expandedSkills);
		if (newExpanded.has(skillId)) {
			newExpanded.delete(skillId);
		} else {
			newExpanded.add(skillId);
		}
		expandedSkills = newExpanded;
	}

	function formatTimestamp(timestamp: number): string {
		return new Date(timestamp * 1000).toLocaleString();
	}

	function formatUptime(seconds: number): string {
		const days = Math.floor(seconds / 86400);
		const hours = Math.floor((seconds % 86400) / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);

		const parts = [];
		if (days > 0) parts.push(`${days}d`);
		if (hours > 0) parts.push(`${hours}h`);
		if (minutes > 0) parts.push(`${minutes}m`);
		if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

		return parts.join(" ");
	}

	function copyToClipboard(text: string) {
		if (typeof navigator !== 'undefined' && navigator.clipboard) {
			navigator.clipboard.writeText(text);
			jsonCopied = true;
			setTimeout(() => {
				jsonCopied = false;
			}, 2000);
		}
	}
</script>

<div class="flex flex-col gap-6">
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Agent Info</h1>
		{#if !agentLoading && !agentError}
			<div class="flex gap-2">
				<button
					class="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
					onclick={() => (showRawJson = !showRawJson)}
				>
					{showRawJson ? "📊 Show Formatted" : "🔍 Show Raw JSON"}
				</button>
				<button
					class="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
					onclick={() => copyToClipboard(rawAgentJson)}
				>
					{jsonCopied ? '✓' : '📋 Copy JSON'}
				</button>
			</div>
		{/if}
	</div>

	{#if agentLoading}
		<div class="flex items-center gap-2 text-gray-500">
			<span class="size-2 animate-pulse rounded-full bg-gray-400"></span>
			Loading agent info...
		</div>
	{:else if agentError}
		<div
			class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
		>
			<p class="text-sm text-red-600 dark:text-red-400">{agentError}</p>
		</div>
	{:else if showRawJson}
		<pre
			class="overflow-x-auto rounded-lg bg-gray-100 p-4 font-mono text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-300">{rawAgentJson}</pre>
	{:else if agentData}
		<!-- Agent Identity Card -->
		<div
			class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<div class="mb-4 flex items-start justify-between">
				<div>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
						{agentData.name}
					</h2>
					<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{agentData.description}</p>
				</div>
				<span
					class="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
				>
					{agentData.kind}
				</span>
			</div>

			<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
				<div>
					<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Agent ID</p>
					<p class="mt-1 font-mono text-xs text-gray-900 dark:text-gray-100">
						{agentData.id ? (typeof agentData.id === 'string' ? agentData.id.substring(0, 8) : String(agentData.id).substring(0, 8)) : 'N/A'}...
					</p>
				</div>
				<div>
					<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Version</p>
					<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
						{agentData.version || 'N/A'}
					</p>
				</div>
				<div>
					<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Protocol</p>
					<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
						{agentData.protocolVersion || 'N/A'}
					</p>
				</div>
				<div>
					<p class="text-xs font-medium text-gray-500 dark:text-gray-400">URL</p>
					{#if agentData.url}
						<a
							href={agentData.url}
							target="_blank"
							rel="noopener noreferrer"
							class="mt-1 block truncate text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
						>
							{agentData.url}
						</a>
					{:else}
						<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">N/A</p>
					{/if}
				</div>
			</div>
		</div>

		<!-- Health Status Section -->
		{#if healthData}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<div class="mb-4 flex items-center justify-between">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Health Status</h3>
					<div class="flex items-center gap-2">
						{#if healthData.status === "ok" && healthData.ready}
							<span class="size-2 rounded-full bg-green-500 animate-pulse"></span>
							<span class="text-sm font-medium text-green-600 dark:text-green-400">Online</span>
						{:else}
							<span class="size-2 rounded-full bg-red-500"></span>
							<span class="text-sm font-medium text-red-600 dark:text-red-400">Offline</span>
						{/if}
					</div>
				</div>

				<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Status</p>
						<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100 capitalize">
							{healthData.status}
						</p>
					</div>
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Ready</p>
						<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
							{healthData.ready ? "Yes" : "No"}
						</p>
					</div>
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Uptime</p>
						<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
							{formatUptime(healthData.uptime_seconds)}
						</p>
					</div>
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Version</p>
						<p class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
							{healthData.version}
						</p>
					</div>
				</div>
			</div>
		{/if}

		<!-- Skills Section -->
		{#if detailedSkills && detailedSkills.length > 0}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
					Skills ({detailedSkills.length})
				</h3>
				<div class="space-y-3">
					{#each detailedSkills as skill}
						<div
							class="rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-600 dark:bg-gray-700/50"
						>
							<!-- Skill Header -->
							<button
								class="w-full p-4 text-left"
								onclick={() => toggleSkillExpansion(skill.id)}
							>
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center gap-2">
											<h4 class="font-semibold text-gray-900 dark:text-white">
												{skill.name}
											</h4>
											<span
												class="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
											>
												v{skill.version}
											</span>
										</div>
										<p class="mt-1 font-mono text-xs text-gray-500 dark:text-gray-400">
											{skill.id}
										</p>
										<p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
											{skill.description.split('\n')[0]}
										</p>
										{#if skill.tags && skill.tags.length > 0}
											<div class="mt-2 flex flex-wrap gap-1">
												{#each skill.tags.slice(0, 4) as tag}
													<span
														class="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-600 dark:text-gray-300"
													>
														#{tag}
													</span>
												{/each}
												{#if skill.tags.length > 4}
													<span
														class="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-600 dark:text-gray-300"
													>
														+{skill.tags.length - 4} more
													</span>
												{/if}
											</div>
										{/if}
									</div>
									<div class="ml-4 flex items-center gap-2">
										<span
											class="text-lg transition-transform {expandedSkills.has(skill.id)
												? 'rotate-180'
												: ''}"
										>
											▼
										</span>
									</div>
								</div>
							</button>

							<!-- Expanded Skill Details -->
							{#if expandedSkills.has(skill.id)}
								<div class="border-t border-gray-200 p-4 dark:border-gray-600">
									<!-- Examples -->
									{#if skill.examples && skill.examples.length > 0}
										<div class="mb-4">
											<h5 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
												Example Queries
											</h5>
											<ul class="space-y-1">
												{#each skill.examples.slice(0, 5) as example}
													<li
														class="text-sm text-gray-600 dark:text-gray-400 before:mr-2 before:content-['•']"
													>
														"{example}"
													</li>
												{/each}
											</ul>
										</div>
									{/if}

									<!-- Input/Output Modes -->
									<div class="mb-4 grid gap-4 md:grid-cols-2">
										{#if skill.input_modes && skill.input_modes.length > 0}
											<div>
												<h5
													class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300"
												>
													Input Modes
												</h5>
												<div class="flex flex-wrap gap-1">
													{#each skill.input_modes as mode}
														<span
															class="rounded bg-green-100 px-2 py-0.5 font-mono text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400"
														>
															{mode}
														</span>
													{/each}
												</div>
											</div>
										{/if}
										{#if skill.output_modes && skill.output_modes.length > 0}
											<div>
												<h5
													class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300"
												>
													Output Modes
												</h5>
												<div class="flex flex-wrap gap-1">
													{#each skill.output_modes as mode}
														<span
															class="rounded bg-purple-100 px-2 py-0.5 font-mono text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
														>
															{mode}
														</span>
													{/each}
												</div>
											</div>
										{/if}
									</div>

									<!-- Performance Metrics -->
									{#if skill.performance}
										<div class="mb-4">
											<h5 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
												Performance
											</h5>
											<div class="grid grid-cols-2 gap-3 md:grid-cols-4">
												{#if skill.performance.avg_processing_time_ms}
													<div>
														<p class="text-xs text-gray-500 dark:text-gray-400">
															Avg Time
														</p>
														<p class="text-sm font-medium text-gray-900 dark:text-gray-100">
															{skill.performance.avg_processing_time_ms}ms
														</p>
													</div>
												{/if}
												{#if skill.performance.max_concurrent_requests}
													<div>
														<p class="text-xs text-gray-500 dark:text-gray-400">
															Max Concurrent
														</p>
														<p class="text-sm font-medium text-gray-900 dark:text-gray-100">
															{skill.performance.max_concurrent_requests}
														</p>
													</div>
												{/if}
												{#if skill.performance.memory_per_request_mb}
													<div>
														<p class="text-xs text-gray-500 dark:text-gray-400">
															Memory/Request
														</p>
														<p class="text-sm font-medium text-gray-900 dark:text-gray-100">
															{skill.performance.memory_per_request_mb}MB
														</p>
													</div>
												{/if}
												{#if skill.performance.scalability}
													<div>
														<p class="text-xs text-gray-500 dark:text-gray-400">
															Scalability
														</p>
														<p
															class="text-sm font-medium capitalize text-gray-900 dark:text-gray-100"
														>
															{skill.performance.scalability}
														</p>
													</div>
												{/if}
											</div>
										</div>
									{/if}

									<!-- Allowed Tools -->
									{#if skill.allowed_tools && skill.allowed_tools.length > 0}
										<div class="mb-4">
											<h5 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
												Allowed Tools
											</h5>
											<div class="flex flex-wrap gap-1">
												{#each skill.allowed_tools as tool}
													<span
														class="rounded bg-orange-100 px-2 py-0.5 text-xs text-orange-700 dark:bg-orange-900/30 dark:text-orange-400"
													>
														{tool}
													</span>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Capabilities Detail -->
									{#if skill.capabilities_detail}
										<div class="mb-4">
											<h5 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
												Capabilities
											</h5>
											<div class="space-y-2">
												{#each Object.entries(skill.capabilities_detail) as [key, value]}
													<div
														class="rounded bg-white p-2 dark:bg-gray-800"
													>
														<p
															class="text-xs font-medium capitalize text-gray-700 dark:text-gray-300"
														>
															{key.replace(/_/g, ' ')}
														</p>
														{#if typeof value === 'object' && value !== null}
															<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">
																{JSON.stringify(value, null, 2)}
															</p>
														{:else}
															<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">
																{value}
															</p>
														{/if}
													</div>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Author & Documentation -->
									<div class="flex items-center justify-between border-t border-gray-200 pt-3 dark:border-gray-600">
										{#if skill.author}
											<p class="text-xs text-gray-500 dark:text-gray-400">
												Author: <span class="font-medium">{skill.author}</span>
											</p>
										{/if}
										{#if skill.has_documentation}
											<a
												href={`/api/agent-skills/${skill.id}`}
												target="_blank"
												rel="noopener noreferrer"
												class="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
											>
												📖 View Full Documentation
											</a>
										{/if}
									</div>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Capabilities Section -->
		<div
			class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Capabilities</h3>
			<div class="space-y-4">
				<div class="grid grid-cols-2 gap-4 md:grid-cols-3">
					<div class="flex items-center gap-2">
						<span class="text-lg">{agentData.capabilities.pushNotifications ? "✅" : "❌"}</span>
						<span class="text-sm text-gray-700 dark:text-gray-300">Push Notifications</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-lg">{agentData.capabilities.streaming ? "✅" : "❌"}</span>
						<span class="text-sm text-gray-700 dark:text-gray-300">Streaming</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-lg">{agentData.telemetry ? "✅" : "❌"}</span>
						<span class="text-sm text-gray-700 dark:text-gray-300">Telemetry</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-lg">{agentData.monitoring ? "✅" : "❌"}</span>
						<span class="text-sm text-gray-700 dark:text-gray-300">Monitoring</span>
					</div>
					<div class="flex items-center gap-2">
						<span class="text-lg">{agentData.debugMode ? "🐛" : "✅"}</span>
						<span class="text-sm text-gray-700 dark:text-gray-300"
							>Debug Mode (Level {agentData.debugLevel})</span
						>
					</div>
				</div>

				{#if agentData.capabilities.extensions && agentData.capabilities.extensions.length > 0}
					<div class="mt-4">
						<h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
							Extensions
						</h4>
						{#each agentData.capabilities.extensions as ext}
							<div
								class="mb-2 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-600 dark:bg-gray-700/50"
							>
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<p class="text-sm font-medium text-gray-900 dark:text-white">
											{ext.description}
										</p>
										<p class="mt-1 font-mono text-xs text-gray-600 dark:text-gray-400">
											{ext.uri}
										</p>
										{#if ext.params}
											<div class="mt-2 space-y-1">
												{#each Object.entries(ext.params) as [key, value]}
													<p class="text-xs text-gray-600 dark:text-gray-400">
														<span class="font-medium">{key}:</span>
														{value}
													</p>
												{/each}
											</div>
										{/if}
									</div>
									<span
										class="ml-2 rounded-full px-2 py-0.5 text-xs {ext.required
											? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
											: 'bg-gray-100 text-gray-600 dark:bg-gray-600 dark:text-gray-300'}"
									>
										{ext.required ? "Required" : "Optional"}
									</span>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Agent Trust Section -->
		{#if agentData.agentTrust}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Trust & Security</h3>
				<div class="grid gap-4 md:grid-cols-2">
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Identity Provider</p>
						<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">
							{agentData.agentTrust.identityProvider || "N/A"}
						</p>
					</div>
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Creator ID</p>
						<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">
							{agentData.agentTrust.creatorId || "N/A"}
						</p>
					</div>
					{#if agentData.agentTrust.creationTimestamp}
						<div>
							<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Created At</p>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">
								{formatTimestamp(agentData.agentTrust.creationTimestamp)}
							</p>
						</div>
					{/if}
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">
							Trust Verification
						</p>
						<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">
							{agentData.agentTrust.trustVerificationRequired ? "Required" : "Not Required"}
						</p>
					</div>
					{#if agentData.agentTrust.inheritedRoles && agentData.agentTrust.inheritedRoles.length > 0}
						<div class="md:col-span-2">
							<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Inherited Roles</p>
							<div class="mt-2 flex flex-wrap gap-2">
								{#each agentData.agentTrust.inheritedRoles as role}
									<span
										class="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
									>
										{role}
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Configuration Section -->
		<div
			class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Configuration</h3>
			<div class="grid gap-4 md:grid-cols-2">
				<div>
					<p class="text-xs font-medium text-gray-500 dark:text-gray-400">History Sessions</p>
					<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">
						{agentData.numHistorySessions}
					</p>
				</div>
				{#if agentData.defaultInputModes && agentData.defaultInputModes.length > 0}
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Input Modes</p>
						<div class="mt-2 flex flex-wrap gap-1">
							{#each agentData.defaultInputModes as mode}
								<span
									class="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-300"
								>
									{mode}
								</span>
							{/each}
						</div>
					</div>
				{/if}
				{#if agentData.defaultOutputModes && agentData.defaultOutputModes.length > 0}
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400">Output Modes</p>
						<div class="mt-2 flex flex-wrap gap-1">
							{#each agentData.defaultOutputModes as mode}
								<span
									class="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-300"
								>
									{mode}
								</span>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Extra Data Section -->
		{#if agentData.extraData && Object.keys(agentData.extraData).length > 0}
			<div
				class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
			>
				<h3 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Additional Info</h3>
				<div class="grid gap-4 md:grid-cols-2">
					{#each Object.entries(agentData.extraData) as [key, value]}
						<div>
							<p class="text-xs font-medium text-gray-500 dark:text-gray-400">
								{key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
							</p>
							<p class="mt-1 text-sm text-gray-900 dark:text-gray-100">
								{typeof value === "number" && key.includes("created")
									? formatTimestamp(value)
									: typeof value === "object"
										? JSON.stringify(value)
										: value}
							</p>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>
