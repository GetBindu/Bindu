<script lang="ts">
	import { onMount } from "svelte";
	import { base } from "$app/paths";
	import { page } from "$app/state";
	import { error as errorStore } from "$lib/stores/errors";

	interface Props {
		/** Optional CSS classes to apply to the button element. */
		classNames?: string;
		/** Text label for the button. */
		label?: string;
	}

	let { classNames = "", label = "Sign in" }: Props = $props();

	/**
	 * Map server-returned OAuth error codes to human-readable messages shown in the toast.
	 * These codes are set by triggerOauthFlow / callback +server.ts when a provider fails.
	 */
	const OAUTH_ERROR_MESSAGES: Record<string, string> = {
		OAUTH_PROVIDER_UNAVAILABLE:
			"Sign-in service is temporarily unavailable. Please try again later.",
		OAUTH_PROVIDER_ERROR: "An error occurred during sign-in. Please try again.",
	};

	/**
	 * On mount, check for an `?error=` query param that the server sets when OAuth fails.
	 * Display the appropriate toast message via the shared error store.
	 */
	onMount(() => {
		const errorCode = page.url.searchParams.get("error");
		if (errorCode && errorCode in OAUTH_ERROR_MESSAGES) {
			errorStore.set(OAUTH_ERROR_MESSAGES[errorCode]);
		} else if (errorCode) {
			// Unknown error code — show a generic message
<!--
	SignInButton component removed because it was not referenced anywhere in the app.
	If a dedicated sign-in button is needed in the future, reintroduce it and wire it
	into the appropriate page or layout so its behavior is exercised.
-->
