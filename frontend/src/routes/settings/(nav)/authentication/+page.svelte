<script lang="ts">
	import { onMount } from "svelte";
	import { browser } from "$app/environment";

	// Agent card state for DID extraction
	type AgentCard = {
		name: string;
		capabilities?: {
			extensions?: Array<{ uri: string; [key: string]: any }>;
		};
	};
	let agentCard = $state<AgentCard | null>(null);
	let agentLoading = $state(true);
	let agentError = $state<string | null>(null);

	// OAuth2 Authentication state
	let authToken = $state<string | null>(
		browser ? localStorage.getItem("bindu_oauth_token") : null
	);
	let authTokenExpiry = $state<number | null>(
		browser ? parseInt(localStorage.getItem("bindu_oauth_expiry") || "0") : null
	);
	let clientSecret = $state("");
	let scope = $state("openid offline agent:read agent:write");
	let authStatus = $state<"idle" | "loading" | "authenticated" | "error">("idle");
	let authError = $state<string | null>(null);
	let authRefreshTimer: ReturnType<typeof setTimeout> | null = null;

	// DID from agent card for OAuth client_id
	let didId = $derived(
		agentCard?.capabilities?.extensions?.find((ext: any) => ext.uri?.startsWith("did:"))
			?.uri || null
	);

	async function authenticateWithOAuth() {
		if (!clientSecret.trim()) {
			authError = "Please enter client secret";
			authStatus = "error";
			return;
		}

		if (!didId) {
			authError = "Agent DID not available";
			authStatus = "error";
			return;
		}

		authStatus = "loading";
		authError = null;

		try {
			const response = await fetch("https://hydra.getbindu.com/oauth2/token", {
				method: "POST",
				headers: { "Content-Type": "application/x-www-form-urlencoded" },
				body: new URLSearchParams({
					grant_type: "client_credentials",
					client_id: didId,
					client_secret: clientSecret,
					scope: scope.trim(),
				}),
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`Authentication failed: ${response.status}`);
			}

			const data = await response.json();
			const { access_token, expires_in } = data;

			if (!access_token) {
				throw new Error("No access token received");
			}

			authToken = access_token;
			const expiryTime = Date.now() + expires_in * 1000;
			authTokenExpiry = expiryTime;

			if (browser && authToken) {
				localStorage.setItem("bindu_oauth_token", authToken);
				localStorage.setItem("bindu_oauth_expiry", expiryTime.toString());
			}

			clientSecret = "";
			authStatus = "authenticated";
			scheduleTokenRefresh(expires_in);
		} catch (err) {
			authError = err instanceof Error ? err.message : "Authentication failed";
			authStatus = "error";
		}
	}

	function clearOAuthToken() {
		authToken = null;
		authTokenExpiry = null;
		authStatus = "idle";
		authError = null;

		if (browser) {
			localStorage.removeItem("bindu_oauth_token");
			localStorage.removeItem("bindu_oauth_expiry");
		}

		if (authRefreshTimer) {
			clearTimeout(authRefreshTimer);
			authRefreshTimer = null;
		}
	}

	function scheduleTokenRefresh(expiresIn: number) {
		if (authRefreshTimer) {
			clearTimeout(authRefreshTimer);
		}

		const refreshTime = (expiresIn - 300) * 1000;
		if (refreshTime > 0) {
			authRefreshTimer = setTimeout(() => {
				clearOAuthToken();
				authStatus = "error";
				authError = "Token expired, please re-authenticate";
			}, refreshTime);
		}
	}

	function checkTokenExpiry() {
		if (authToken && authTokenExpiry) {
			const now = Date.now();
			if (now >= authTokenExpiry) {
				clearOAuthToken();
				authStatus = "error";
				authError = "Token expired";
			}
		}
	}

	function getTimeRemaining(): string {
		if (!authTokenExpiry) return "";
		const now = Date.now();
		const diff = authTokenExpiry - now;
		if (diff <= 0) return "Expired";
		const minutes = Math.floor(diff / 60000);
		const seconds = Math.floor((diff % 60000) / 1000);
		return `${minutes}m ${seconds}s`;
	}

	function getExpirationTime(): string {
		if (!authTokenExpiry) return "";
		const expiryDate = new Date(authTokenExpiry);
		return expiryDate.toLocaleTimeString([], { 
			hour: '2-digit', 
			minute: '2-digit',
			second: '2-digit',
			hour12: true 
		});
	}

	// Real-time countdown update
	let countdownInterval: ReturnType<typeof setInterval> | null = null;
	let timeDisplay = $state(getTimeRemaining());
	let expiryTimeDisplay = $state(getExpirationTime());
	let showFullToken = $state(false);
	let tokenCopied = $state(false);

	function getMaskedToken(): string {
		if (!authToken) return "";
		if (showFullToken) return authToken;
		// Show first 8 and last 4 characters
		if (authToken.length <= 12) return authToken;
		return `${authToken.substring(0, 8)}...${authToken.substring(authToken.length - 4)}`;
	}

	function copyTokenToClipboard() {
		if (authToken) {
			navigator.clipboard.writeText(authToken);
			tokenCopied = true;
			setTimeout(() => {
				tokenCopied = false;
			}, 2000);
		}
	}

	$effect(() => {
		if (authStatus === 'authenticated' && authTokenExpiry) {
			if (countdownInterval) clearInterval(countdownInterval);
			
			countdownInterval = setInterval(() => {
				timeDisplay = getTimeRemaining();
				expiryTimeDisplay = getExpirationTime();
			}, 1000);
		} else {
			if (countdownInterval) {
				clearInterval(countdownInterval);
				countdownInterval = null;
			}
		}
	});

	onMount(() => {
		// Fetch agent card for DID
		fetch("/api/agent-card")
			.then((res) => {
				if (res.ok) {
					return res.json();
				} else {
					agentError = "Could not load agent info";
					return null;
				}
			})
			.then((data) => {
				if (data) {
					agentCard = data;
				}
			})
			.catch(() => {
				agentError = "Agent not connected";
			})
			.finally(() => {
				agentLoading = false;
			});

		// Initialize auth state
		if (authToken && authTokenExpiry) {
			const now = Date.now();
			if (now < authTokenExpiry) {
				authStatus = "authenticated";
				const remainingSeconds = Math.floor((authTokenExpiry - now) / 1000);
				scheduleTokenRefresh(remainingSeconds);
			} else {
				clearOAuthToken();
			}
		}

		const interval = setInterval(checkTokenExpiry, 60000);
		return () => {
			clearInterval(interval);
			if (authRefreshTimer) clearTimeout(authRefreshTimer);
			if (countdownInterval) clearInterval(countdownInterval);
		};
	});
</script>

<div class="flex w-full flex-col gap-6">
	<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Authentication</h1>

	<div
		class="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
	>
		<div class="flex flex-col gap-5">
			<!-- Status Display -->
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Status:</span>
					{#if authStatus === "authenticated"}
						<span
							class="flex items-center gap-2 text-sm font-medium text-green-600 dark:text-green-400"
						>
							<span class="size-2 animate-pulse rounded-full bg-green-500"></span>
							Authenticated
						</span>
					{:else if authStatus === "loading"}
						<span
							class="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400"
						>
							<span class="size-2 animate-pulse rounded-full bg-blue-500"></span>
							Authenticating...
						</span>
					{:else if authStatus === "error"}
						<span
							class="flex items-center gap-2 text-sm font-medium text-red-600 dark:text-red-400"
						>
							<span class="size-2 rounded-full bg-red-500"></span>
							Error
						</span>
					{:else}
						<span class="text-sm text-gray-500 dark:text-gray-400">Not authenticated</span>
					{/if}
				</div>
				{#if authStatus === "authenticated" && authTokenExpiry}
					<div class="flex flex-col items-end gap-0.5">
						<span class="text-xs font-medium text-gray-600 dark:text-gray-400">
							{timeDisplay}
						</span>
						<span class="text-[10px] text-gray-500 dark:text-gray-500">
							Expires at {expiryTimeDisplay}
						</span>
					</div>
				{/if}
			</div>

			<!-- Error Message -->
			{#if authError}
				<div
					class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400"
				>
					{authError}
				</div>
			{/if}

			<!-- Client ID (DID) Display -->
			{#if agentLoading}
				<div class="flex items-center gap-2 text-sm text-gray-500">
					<span class="size-2 animate-pulse rounded-full bg-gray-400"></span>
					Loading agent info...
				</div>
			{:else if agentError}
				<div class="text-sm text-red-600 dark:text-red-400">{agentError}</div>
			{:else if didId}
				<div>
					<label class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
						Client ID
					</label>
					<code
						class="block break-all rounded-lg bg-gray-100 px-4 py-3 font-mono text-xs text-gray-800 dark:bg-gray-700 dark:text-gray-200"
					>
						{didId}
					</code>
				</div>
			{/if}

			<!-- Client Secret Input -->
			<div>
				<label
					for="client-secret"
					class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
				>
					Client Secret
				</label>
				<input
					id="client-secret"
					type="password"
					bind:value={clientSecret}
					placeholder="Enter your client secret"
					disabled={authStatus === "loading" || authStatus === "authenticated"}
					class="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500 dark:disabled:bg-gray-800"
				/>
			</div>

			<!-- Scope Input -->
			<div>
				<label
					for="scope"
					class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
				>
					Scope
				</label>
				<input
					id="scope"
					type="text"
					bind:value={scope}
					placeholder="openid offline agent:read agent:write"
					disabled={authStatus === "loading" || authStatus === "authenticated"}
					class="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 font-mono text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:placeholder-gray-500 dark:disabled:bg-gray-800"
				/>
			</div>

			<!-- Access Token Display -->
			{#if authStatus === "authenticated" && authToken}
				<div>
					<h3 class="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
						Access Token
					</h3>
					<div class="flex items-center gap-2">
						<code
							class="flex-1 overflow-x-auto rounded-lg bg-gray-100 px-4 py-3 font-mono text-xs text-gray-800 dark:bg-gray-700 dark:text-gray-200"
						>
							{getMaskedToken()}
						</code>
						<button
							type="button"
							onclick={() => (showFullToken = !showFullToken)}
							class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
							title={showFullToken ? "Hide token" : "Show full token"}
						>
							{showFullToken ? "👁️" : "👁️‍🗨️"}
						</button>
						<button
							type="button"
							onclick={copyTokenToClipboard}
							class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
							title="Copy to clipboard"
						>
							{tokenCopied ? '✓' : '📋'}
						</button>
					</div>
				</div>
			{/if}

			<!-- Action Buttons -->
			<div class="flex gap-3">
				{#if authStatus === "authenticated"}
					<button
						type="button"
						onclick={clearOAuthToken}
						class="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
					>
						Clear Token
					</button>
				{:else}
					<button
						type="button"
						onclick={authenticateWithOAuth}
						disabled={authStatus === "loading" || !clientSecret.trim() || !didId}
						class="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300 dark:disabled:bg-gray-700"
					>
						{authStatus === "loading" ? "Authenticating..." : "Authenticate"}
					</button>
				{/if}
			</div>

			<!-- Info Text -->
			<div
				class="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 dark:border-blue-900/30 dark:bg-blue-900/10"
			>
				<p class="text-xs text-blue-800 dark:text-blue-300">
					<strong>OAuth2 Authentication:</strong> This uses the Hydra OAuth2 server at
					<code class="rounded bg-blue-100 px-1 py-0.5 dark:bg-blue-900/30"
						>hydra.getbindu.com</code
					>. Your token is valid for 1 hour and stored locally in your browser. The token will
					automatically expire 5 minutes before the TTL ends.
				</p>
			</div>
		</div>
	</div>
</div>
