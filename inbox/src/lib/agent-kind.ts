import type { EcosystemAgent } from "~/lib/api-types";

/** Heuristic: is this ecosystem entry a gateway?
 *
 * We use the id + card name today — both the server-side plan router
 * and the sidebar grouping depend on the same definition, so it lives
 * in one place. Sturdier detection (probing /health for
 * `runtime.planner`) belongs at the live-fetch site, not here — this
 * helper has to work off the cached row alone. */
export function isGateway(a: EcosystemAgent): boolean {
	const id = a.id.toLowerCase();
	const name = (a.agentCard?.name ?? "").toLowerCase();
	return /gateway/.test(id) || /gateway/.test(name);
}
