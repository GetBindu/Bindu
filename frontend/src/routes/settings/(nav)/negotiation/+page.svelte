<script lang="ts">
	import { browser } from "$app/environment";

	interface NegotiationRequest {
		task_summary: string;
		task_details: string;
		input_mime_types: string[];
		output_mime_types: string[];
		max_latency_ms: number;
		max_cost_amount: string;
		required_tools: string[];
		forbidden_tools: string[];
		min_score: number;
		weights: {
			skill_match: number;
			io_compatibility: number;
			performance: number;
			load: number;
			cost: number;
		};
	}

	interface SkillMatch {
		skill_id: string;
		skill_name: string;
		score: number;
		reasons: string[];
	}

	interface NegotiationResponse {
		accepted: boolean;
		score: number;
		confidence: number;
		rejection_reason?: string;
		skill_matches: SkillMatch[];
		matched_tags: string[];
		matched_capabilities: string[];
		latency_estimate_ms: number;
		queue_depth: number;
		subscores: {
			skill_match: number;
			io_compatibility: number;
			load: number;
			cost: number;
		};
	}

	// Form state
	let taskSummary = $state("Extract tables and text from PDF invoices and text");
	let taskDetails = $state(
		"Need to process multiple invoice PDFs and extract structured data including line items, totals, and vendor information"
	);
	let inputMimeTypes = $state("application/pdf");
	let outputMimeTypes = $state("application/json");
	let maxLatencyMs = $state(5000);
	let maxCostAmount = $state("0.001");
	let requiredTools = $state("");
	let forbiddenTools = $state("");
	let minScore = $state(0.7);
	let skillMatchWeight = $state(0.6);
	let ioCompatibilityWeight = $state(0.2);
	let performanceWeight = $state(0.1);
	let loadWeight = $state(0.05);
	let costWeight = $state(0.05);

	// Response state
	let negotiationStatus = $state<"idle" | "loading" | "success" | "error">("idle");
	let negotiationError = $state<string | null>(null);
	let negotiationResponse = $state<NegotiationResponse | null>(null);

	// Get auth token from localStorage
	let authToken = $state<string | null>(
		browser ? localStorage.getItem("bindu_oauth_token") : null
	);

	// Results section ref for auto-scroll
	let resultsSection: HTMLDivElement | null = null;

	async function testNegotiation() {
		if (!authToken) {
			negotiationError = "Please authenticate first in the Authentication section";
			negotiationStatus = "error";
			return;
		}

		negotiationStatus = "loading";
		negotiationError = null;
		negotiationResponse = null;

		const request: NegotiationRequest = {
			task_summary: taskSummary,
			task_details: taskDetails,
			input_mime_types: inputMimeTypes.split(",").map((t) => t.trim()).filter(Boolean),
			output_mime_types: outputMimeTypes.split(",").map((t) => t.trim()).filter(Boolean),
			max_latency_ms: maxLatencyMs,
			max_cost_amount: maxCostAmount,
			required_tools: requiredTools.split(",").map((t) => t.trim()).filter(Boolean),
			forbidden_tools: forbiddenTools.split(",").map((t) => t.trim()).filter(Boolean),
			min_score: minScore,
			weights: {
				skill_match: skillMatchWeight,
				io_compatibility: ioCompatibilityWeight,
				performance: performanceWeight,
				load: loadWeight,
				cost: costWeight,
			},
		};

		try {
			// Use API proxy endpoint
			const response = await fetch("/api/agent-negotiation", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${authToken}`,
				},
				body: JSON.stringify(request),
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`Negotiation failed: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			negotiationResponse = data;
			negotiationStatus = "success";

			// Auto-scroll to results after a short delay
			setTimeout(() => {
				if (resultsSection) {
					resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
				}
			}, 100);
		} catch (err) {
			negotiationError = err instanceof Error ? err.message : "Negotiation request failed";
			negotiationStatus = "error";
		}
	}

	function resetForm() {
		negotiationStatus = "idle";
		negotiationError = null;
		negotiationResponse = null;
	}
</script>

<div class="flex w-full flex-col gap-6">
	<div>
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Negotiation</h1>
		<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
			Test agent negotiation API to see if this agent can handle your task
		</p>
	</div>

	<!-- Request Form -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
	>
		<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Task Details</h2>

		<div class="space-y-4">
			<!-- Task Summary -->
			<div>
				<label for="task-summary" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Task Summary
				</label>
				<input
					id="task-summary"
					type="text"
					bind:value={taskSummary}
					placeholder="Brief description of the task"
					class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
				/>
			</div>

			<!-- Task Details -->
			<div>
				<label for="task-details" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Task Details
				</label>
				<textarea
					id="task-details"
					bind:value={taskDetails}
					placeholder="Detailed description of the task requirements"
					rows="3"
					class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
				></textarea>
			</div>

			<!-- MIME Types -->
			<div class="grid gap-4 md:grid-cols-2">
				<div>
					<label for="input-mime" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Input MIME Types (comma-separated)
					</label>
					<input
						id="input-mime"
						type="text"
						bind:value={inputMimeTypes}
						placeholder="application/pdf, text/plain"
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 font-mono text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
					/>
				</div>
				<div>
					<label for="output-mime" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Output MIME Types (comma-separated)
					</label>
					<input
						id="output-mime"
						type="text"
						bind:value={outputMimeTypes}
						placeholder="application/json, text/plain"
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 font-mono text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
					/>
				</div>
			</div>

			<!-- Constraints -->
			<div class="grid gap-4 md:grid-cols-3">
				<div>
					<label for="max-latency" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Max Latency (ms)
					</label>
					<input
						id="max-latency"
						type="number"
						bind:value={maxLatencyMs}
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
					/>
				</div>
				<div>
					<label for="max-cost" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Max Cost Amount
					</label>
					<input
						id="max-cost"
						type="text"
						bind:value={maxCostAmount}
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 font-mono text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
					/>
				</div>
				<div>
					<label for="min-score" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Min Score (0-1)
					</label>
					<input
						id="min-score"
						type="number"
						step="0.1"
						min="0"
						max="1"
						bind:value={minScore}
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
					/>
				</div>
			</div>

			<!-- Tools -->
			<div class="grid gap-4 md:grid-cols-2">
				<div>
					<label for="required-tools" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Required Tools (comma-separated)
					</label>
					<input
						id="required-tools"
						type="text"
						bind:value={requiredTools}
						placeholder="tool1, tool2"
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 font-mono text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
					/>
				</div>
				<div>
					<label for="forbidden-tools" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Forbidden Tools (comma-separated)
					</label>
					<input
						id="forbidden-tools"
						type="text"
						bind:value={forbiddenTools}
						placeholder="tool3, tool4"
						class="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 font-mono text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
					/>
				</div>
			</div>

			<!-- Weights -->
			<div>
				<h3 class="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Scoring Weights</h3>
				<div class="grid gap-3 md:grid-cols-5">
					<div>
						<label for="skill-weight" class="mb-1 block text-xs text-gray-600 dark:text-gray-400">
							Skill Match
						</label>
						<input
							id="skill-weight"
							type="number"
							step="0.05"
							min="0"
							max="1"
							bind:value={skillMatchWeight}
							class="w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
						/>
					</div>
					<div>
						<label for="io-weight" class="mb-1 block text-xs text-gray-600 dark:text-gray-400">
							I/O Compatibility
						</label>
						<input
							id="io-weight"
							type="number"
							step="0.05"
							min="0"
							max="1"
							bind:value={ioCompatibilityWeight}
							class="w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
						/>
					</div>
					<div>
						<label for="perf-weight" class="mb-1 block text-xs text-gray-600 dark:text-gray-400">
							Performance
						</label>
						<input
							id="perf-weight"
							type="number"
							step="0.05"
							min="0"
							max="1"
							bind:value={performanceWeight}
							class="w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
						/>
					</div>
					<div>
						<label for="load-weight" class="mb-1 block text-xs text-gray-600 dark:text-gray-400">
							Load
						</label>
						<input
							id="load-weight"
							type="number"
							step="0.05"
							min="0"
							max="1"
							bind:value={loadWeight}
							class="w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
						/>
					</div>
					<div>
						<label for="cost-weight" class="mb-1 block text-xs text-gray-600 dark:text-gray-400">
							Cost
						</label>
						<input
							id="cost-weight"
							type="number"
							step="0.05"
							min="0"
							max="1"
							bind:value={costWeight}
							class="w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
						/>
					</div>
				</div>
			</div>

			<!-- Action Buttons -->
			<div class="flex gap-3 pt-2">
				<button
					type="button"
					onclick={testNegotiation}
					disabled={negotiationStatus === "loading" || !authToken}
					class="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300 dark:disabled:bg-gray-700"
				>
					{negotiationStatus === "loading" ? "Testing..." : "Test Negotiation"}
				</button>
				{#if negotiationResponse}
					<button
						type="button"
						onclick={resetForm}
						class="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
					>
						Reset
					</button>
				{/if}
			</div>

			{#if !authToken}
				<div class="rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20">
					<p class="text-sm text-yellow-800 dark:text-yellow-300">
						⚠️ Please authenticate first in the Authentication section to test negotiation
					</p>
				</div>
			{/if}
		</div>
	</div>

	<!-- Error Display -->
	{#if negotiationError}
		<div
			class="rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
		>
			<p class="text-sm font-medium text-red-600 dark:text-red-400">{negotiationError}</p>
		</div>
	{/if}

	<!-- Response Display -->
	{#if negotiationResponse}
		<div
			bind:this={resultsSection}
			class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Negotiation Result</h2>

			<!-- Acceptance Status -->
			<div class="mb-6 flex items-center gap-4">
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Status:</span>
					{#if negotiationResponse.accepted}
						<span
							class="flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
						>
							<span class="size-2 rounded-full bg-green-500"></span>
							Accepted
						</span>
					{:else}
						<span
							class="flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400"
						>
							<span class="size-2 rounded-full bg-red-500"></span>
							Rejected
						</span>
					{/if}
				</div>
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Score:</span>
					<span class="text-lg font-bold text-gray-900 dark:text-white">
						{negotiationResponse.score.toFixed(4)}
					</span>
				</div>
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Confidence:</span>
					<span class="text-lg font-bold text-gray-900 dark:text-white">
						{negotiationResponse.confidence.toFixed(2)}
					</span>
				</div>
			</div>

			{#if negotiationResponse.rejection_reason}
				<div class="mb-4 rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
					<p class="text-sm text-red-700 dark:text-red-400">
						<strong>Rejection Reason:</strong>
						{negotiationResponse.rejection_reason}
					</p>
				</div>
			{/if}

			<!-- Subscores -->
			<div class="mb-6">
				<h3 class="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">Subscores</h3>
				<div class="grid gap-3 md:grid-cols-4">
					<div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
						<p class="text-xs text-gray-500 dark:text-gray-400">Skill Match</p>
						<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
							{negotiationResponse.subscores.skill_match.toFixed(4)}
						</p>
					</div>
					<div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
						<p class="text-xs text-gray-500 dark:text-gray-400">I/O Compatibility</p>
						<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
							{negotiationResponse.subscores.io_compatibility.toFixed(4)}
						</p>
					</div>
					<div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
						<p class="text-xs text-gray-500 dark:text-gray-400">Load</p>
						<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
							{negotiationResponse.subscores.load.toFixed(4)}
						</p>
					</div>
					<div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
						<p class="text-xs text-gray-500 dark:text-gray-400">Cost</p>
						<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
							{negotiationResponse.subscores.cost.toFixed(4)}
						</p>
					</div>
				</div>
			</div>

			<!-- Skill Matches -->
			{#if negotiationResponse.skill_matches.length > 0}
				<div class="mb-6">
					<h3 class="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">
						Matched Skills
					</h3>
					<div class="space-y-3">
						{#each negotiationResponse.skill_matches as skillMatch}
							<div
								class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-600 dark:bg-gray-700/50"
							>
								<div class="flex items-start justify-between">
									<div class="flex-1">
										<div class="flex items-center gap-2">
											<span class="font-medium text-gray-900 dark:text-white">
												{skillMatch.skill_name}
											</span>
											<span class="font-mono text-xs text-gray-500 dark:text-gray-400">
												{skillMatch.skill_id}
											</span>
										</div>
										<div class="mt-2 flex flex-wrap gap-1">
											{#each skillMatch.reasons as reason}
												<span
													class="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
												>
													{reason}
												</span>
											{/each}
										</div>
									</div>
									<span class="ml-4 text-lg font-bold text-gray-900 dark:text-white">
										{skillMatch.score.toFixed(4)}
									</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Matched Tags & Capabilities -->
			<div class="grid gap-4 md:grid-cols-2">
				{#if negotiationResponse.matched_tags.length > 0}
					<div>
						<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
							Matched Tags
						</h3>
						<div class="flex flex-wrap gap-1">
							{#each negotiationResponse.matched_tags as tag}
								<span
									class="rounded-full bg-green-100 px-2 py-1 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400"
								>
									#{tag}
								</span>
							{/each}
						</div>
					</div>
				{/if}
				{#if negotiationResponse.matched_capabilities.length > 0}
					<div>
						<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
							Matched Capabilities
						</h3>
						<div class="flex flex-wrap gap-1">
							{#each negotiationResponse.matched_capabilities as capability}
								<span
									class="rounded-full bg-purple-100 px-2 py-1 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
								>
									{capability}
								</span>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<!-- Performance Metrics -->
			<div class="mt-6 grid gap-4 md:grid-cols-2">
				<div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
					<p class="text-xs text-gray-500 dark:text-gray-400">Latency Estimate</p>
					<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
						{negotiationResponse.latency_estimate_ms}ms
					</p>
				</div>
				<div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
					<p class="text-xs text-gray-500 dark:text-gray-400">Queue Depth</p>
					<p class="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
						{negotiationResponse.queue_depth}
					</p>
				</div>
			</div>
		</div>
	{/if}
</div>
