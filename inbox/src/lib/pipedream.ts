/** Pipedream Connect integration.
 *
 * Flow:
 *   1. The SDK calls our token callback whenever it needs a Connect token.
 *      The callback hits `/api/pipedream/connect-token` on the comms
 *      server, which holds `PIPEDREAM_PROJECT_ID/CLIENT_ID/CLIENT_SECRET`
 *      and mints a project-scoped token. We never put the client secret
 *      in the browser.
 *   2. `connectAccount({ app, onSuccess, … })` opens Pipedream's iframe,
 *      runs the OAuth flow against the target app (gmail / notion), and
 *      resolves with an account `id`.
 *   3. We return only the `accountId` to the caller. The wizard stores it
 *      via `POST /api/me`; the spawn step later (Phase 3) turns it into
 *      an MCP server URL the agno agent can consume.
 *
 * The SDK is loaded dynamically so the wizard's main bundle doesn't pay
 * for it on first paint — only when the user clicks Connect. If the
 * server returns 501 (Pipedream not configured), we surface that error
 * verbatim instead of crashing the popup. */

import { postJson } from "~/lib/fetch";

export type PipedreamApp = "gmail" | "notion";

export type ConnectResult =
	| { ok: true; accountId: string }
	| { ok: false; errMsg: string };

/** External-user-id used when minting tokens. For the personal-agent
 * onboarding there's exactly one operator per comms instance, so a
 * fixed value is fine. When we add multi-tenant support, this becomes
 * the operator's session id. */
const OPERATOR_EXTERNAL_ID = "comms-operator";

export async function connectPipedreamApp(
	app: PipedreamApp,
): Promise<ConnectResult> {
	// Probe once for a token so we can give a clean "not configured"
	// error before opening the iframe. The SDK will hit the callback
	// again when it actually needs the token; that's fine — the comms
	// server endpoint is idempotent and cheap.
	const probe = await postJson<unknown>("/api/pipedream/connect-token", {
		external_user_id: OPERATOR_EXTERNAL_ID,
	});
	if (!probe.ok) {
		return {
			ok: false,
			errMsg: probe.errMsg ?? "Could not obtain a Pipedream Connect token.",
		};
	}

	let createFrontendClient: typeof import("@pipedream/sdk/browser").createFrontendClient;
	try {
		({ createFrontendClient } = await import("@pipedream/sdk/browser"));
	} catch {
		return {
			ok: false,
			errMsg:
				"Pipedream SDK not installed. Run `npm i @pipedream/sdk` in inbox.",
		};
	}

	const pd = createFrontendClient({
		externalUserId: OPERATOR_EXTERNAL_ID,
		// SDK calls this when it needs a fresh token. The shape it expects
		// matches what Pipedream's server `tokens.create` returns — which
		// is exactly what our /api/pipedream/connect-token proxies through.
		tokenCallback: async () => {
			const res = await postJson<Record<string, unknown>>(
				"/api/pipedream/connect-token",
				{ external_user_id: OPERATOR_EXTERNAL_ID },
			);
			if (!res.ok || !res.data) {
				throw new Error(res.errMsg ?? "token mint failed");
			}
			// biome-ignore lint/suspicious/noExplicitAny: SDK accepts the
			// raw token response shape; typing it here would duplicate
			// Pipedream's internal type that they don't export cleanly.
			return res.data as any;
		},
	});

	return new Promise<ConnectResult>((resolve) => {
		// Both onSuccess and onClose can fire; we resolve on the first
		// signal that gives us a verdict. Guard with a flag so we don't
		// resolve twice if Pipedream emits both.
		let settled = false;
		const settle = (r: ConnectResult) => {
			if (settled) return;
			settled = true;
			resolve(r);
		};
		void pd.connectAccount({
			app,
			onSuccess: (res) => settle({ ok: true, accountId: res.id }),
			onError: (err) =>
				settle({ ok: false, errMsg: err.message ?? "connect failed" }),
			onClose: (status) => {
				if (!status.successful) {
					settle({ ok: false, errMsg: "Popup closed before connecting." });
				}
			},
		});
	});
}
