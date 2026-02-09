<script lang="ts">
	import { browser } from "$app/environment";

	interface DIDDocument {
		"@context": string[];
		id: string;
		created: string;
		authentication: Array<{
			id: string;
			type: string;
			controller: string;
			publicKeyBase58: string;
		}>;
	}

	// Form state
	let didInput = $state("did:bindu:your_email_at_example_com:research_agent:9e84d316dd68482683ca3b3efc9c5500");

	// Response state
	let resolveStatus = $state<"idle" | "loading" | "success" | "error">("idle");
	let resolveError = $state<string | null>(null);
	let didDocument = $state<DIDDocument | null>(null);

	// Get auth token from localStorage
	let authToken = $state<string | null>(
		browser ? localStorage.getItem("bindu_oauth_token") : null
	);

	// Results section ref for auto-scroll
	let resultsSection: HTMLDivElement | null = null;

	// Copy feedback state
	let copiedItems = $state<Record<string, boolean>>({});

	function showCopyFeedback(itemId: string) {
		copiedItems[itemId] = true;
		setTimeout(() => {
			copiedItems[itemId] = false;
		}, 2000);
	}

	async function resolveDID() {
		if (!didInput.trim()) {
			resolveError = "Please enter a DID";
			resolveStatus = "error";
			return;
		}

		resolveStatus = "loading";
		resolveError = null;
		didDocument = null;

		try {
			const response = await fetch("/api/did-resolve", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
				},
				body: JSON.stringify({ did: didInput.trim() }),
			});

			if (!response.ok) {
				throw new Error(`DID resolution failed: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			didDocument = data;
			resolveStatus = "success";

			// Auto-scroll to results after a short delay
			setTimeout(() => {
				if (resultsSection) {
					resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
				}
			}, 100);
		} catch (err) {
			resolveError = err instanceof Error ? err.message : "DID resolution failed";
			resolveStatus = "error";
		}
	}

	function resetForm() {
		resolveStatus = "idle";
		resolveError = null;
		didDocument = null;
	}

	function copyToClipboard(text: string, itemId: string) {
		if (browser) {
			navigator.clipboard.writeText(text);
			showCopyFeedback(itemId);
		}
	}
</script>

<div class="flex w-full flex-col gap-6">
	<div>
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">DID Resolve</h1>
		<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
			Resolve Decentralized Identifiers (DIDs) to retrieve DID documents
		</p>
	</div>

	<!-- Input Form -->
	<div
		class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex flex-col gap-4">
			<!-- DID Input -->
			<div>
				<label for="did-input" class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
					Decentralized Identifier (DID)
				</label>
				<input
					id="did-input"
					type="text"
					bind:value={didInput}
					placeholder="did:bindu:your_email_at_example_com:agent_name:hash"
					class="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 font-mono text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500"
				/>
			</div>

			<!-- Action Buttons -->
			<div class="flex gap-3">
				<button
					type="button"
					onclick={resolveDID}
					disabled={resolveStatus === "loading" || !didInput.trim()}
					class="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300 dark:disabled:bg-gray-700"
				>
					{resolveStatus === "loading" ? "Resolving..." : "Resolve DID"}
				</button>
				{#if didDocument}
					<button
						type="button"
						onclick={resetForm}
						class="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
					>
						Reset
					</button>
				{/if}
			</div>

			<!-- Info Text -->
			<div
				class="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 dark:border-blue-900/30 dark:bg-blue-900/10"
			>
				<p class="text-xs text-blue-800 dark:text-blue-300">
					<strong>DID Resolution:</strong> Enter a Bindu DID to retrieve its DID document, which
					contains authentication keys and verification methods.
				</p>
			</div>
		</div>
	</div>

	<!-- Error Display -->
	{#if resolveError}
		<div
			class="rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
		>
			<p class="text-sm font-medium text-red-600 dark:text-red-400">{resolveError}</p>
		</div>
	{/if}

	<!-- DID Document Display -->
	{#if didDocument}
		<div
			bind:this={resultsSection}
			class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
		>
			<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">DID Document</h2>

			<!-- DID ID -->
			<div class="mb-6">
				<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Identifier</h3>
				<div class="flex items-center gap-2">
					<code
						class="flex-1 overflow-x-auto rounded-lg bg-gray-100 px-4 py-3 font-mono text-xs text-gray-800 dark:bg-gray-700 dark:text-gray-200"
					>
						{didDocument.id}
					</code>
					<button
						type="button"
						onclick={() => didDocument && copyToClipboard(didDocument.id, 'did-id')}
						class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
						title="Copy to clipboard"
					>
						{copiedItems['did-id'] ? '✓' : '📋'}
					</button>
				</div>
			</div>

			<!-- Created Date -->
			<div class="mb-6">
				<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Created</h3>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					{new Date(didDocument.created).toLocaleString()}
				</p>
			</div>

			<!-- Context -->
			<div class="mb-6">
				<h3 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Context</h3>
				<div class="space-y-1">
					{#each didDocument["@context"] as context}
						<div
							class="rounded-lg bg-gray-50 px-3 py-2 font-mono text-xs text-gray-700 dark:bg-gray-700/50 dark:text-gray-300"
						>
							{context}
						</div>
					{/each}
				</div>
			</div>

			<!-- Authentication Methods -->
			{#if didDocument.authentication && didDocument.authentication.length > 0}
				<div>
					<h3 class="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">
						Authentication Methods
					</h3>
					<div class="space-y-4">
						{#each didDocument.authentication as auth}
							<div
								class="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-600 dark:bg-gray-700/50"
							>
								<div class="mb-3 flex items-start justify-between">
									<div class="flex-1">
										<div class="mb-1 flex items-center gap-2">
											<span
												class="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
											>
												{auth.type}
											</span>
										</div>
										<p class="mt-2 font-mono text-xs text-gray-500 dark:text-gray-400">
											{auth.id}
										</p>
									</div>
								</div>

								<div class="space-y-3">
									<div>
										<p class="mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
											Controller
										</p>
										<code
											class="block break-all rounded bg-gray-100 px-3 py-2 font-mono text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-200"
										>
											{auth.controller}
										</code>
									</div>

									<div>
										<div class="mb-1 flex items-center justify-between">
											<p class="text-xs font-medium text-gray-600 dark:text-gray-400">
												Public Key (Base58)
											</p>
											<button
												type="button"
												onclick={() => copyToClipboard(auth.publicKeyBase58, `pubkey-${auth.id}`)}
												class="rounded border border-gray-300 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
												title="Copy public key"
											>
												{copiedItems[`pubkey-${auth.id}`] ? '✓' : '📋'}
											</button>
										</div>
										<code
											class="block break-all rounded bg-gray-100 px-3 py-2 font-mono text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-200"
										>
											{auth.publicKeyBase58}
										</code>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Raw JSON -->
			<div class="mt-6">
				<details class="group">
					<summary
						class="flex cursor-pointer items-center justify-between text-sm font-semibold text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
					>
						<span>View Raw JSON</span>
						<button
							type="button"
							onclick={(e) => {
								e.preventDefault();
								didDocument && copyToClipboard(JSON.stringify(didDocument, null, 2), 'json');
							}}
							class="ml-2 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
							title="Copy JSON to clipboard"
						>
							{copiedItems['json'] ? '✓' : '📋 Copy JSON'}
						</button>
					</summary>
					<pre
						class="mt-3 overflow-x-auto rounded-lg bg-gray-100 p-4 font-mono text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-300">{JSON.stringify(didDocument, null, 2)}</pre>
				</details>
			</div>
		</div>
	{/if}
</div>
