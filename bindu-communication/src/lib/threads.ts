import type { StreamEvent } from "~/types";

export interface Thread {
	contextId: string;
	latest: StreamEvent;
	totalCount: number;
	attentionCount: number;
	latestTs: string;
}

/**
 * Group events into Gmail-style threads keyed by their A2A `context_id`.
 *
 * - Events without a context_id (heartbeats, gateway plan-step parents)
 *   are skipped — they don't belong to any conversation.
 * - The `latest` event represents the row preview; sort order is by
 *   `latestTs` DESC so newest threads land on top.
 * - `attentionCount` tells the UI whether to pin a thread above the
 *   regular feed and show the sunflower badge.
 */
export function groupByThread(events: StreamEvent[]): Thread[] {
	const byCtx = new Map<string, Thread>();
	for (const e of events) {
		const ctx = extractContextId(e);
		if (!ctx) continue;
		const existing = byCtx.get(ctx);
		if (!existing) {
			byCtx.set(ctx, {
				contextId: ctx,
				latest: e,
				totalCount: 1,
				attentionCount: e.needsAttention ? 1 : 0,
				latestTs: e.ts,
			});
			continue;
		}
		existing.totalCount += 1;
		if (e.needsAttention) existing.attentionCount += 1;
		if (e.ts > existing.latestTs) {
			existing.latest = e;
			existing.latestTs = e.ts;
		}
	}
	return Array.from(byCtx.values()).sort((a, b) => {
		// Attention threads pinned to top, then by latest timestamp DESC.
		const a1 = a.attentionCount > 0 ? 1 : 0;
		const b1 = b.attentionCount > 0 ? 1 : 0;
		if (a1 !== b1) return b1 - a1;
		return b.latestTs.localeCompare(a.latestTs);
	});
}

/**
 * Pull a usable thread key off any event shape:
 * - A2A live events carry payload.context_id — that's the real thread id.
 * - Events without one (mock scenarios, gateway plan-step rows whose
 *   payload uses sessionID instead of context_id) fall back to the
 *   counterparty DID so they still group sensibly (one thread per
 *   correspondent / per gateway session).
 */
function extractContextId(e: StreamEvent): string | null {
	if (e.payload) {
		try {
			const p = JSON.parse(e.payload) as { context_id?: string };
			if (typeof p.context_id === "string" && p.context_id.length > 0) {
				return p.context_id;
			}
		} catch {
			// fall through
		}
	}
	if (e.counterparty?.did) return e.counterparty.did;
	return null;
}

export function shortContextId(ctx: string): string {
	if (ctx.length <= 12) return ctx;
	// DID-style keys (did:bindu:…) get the existing DID short rendering
	if (ctx.startsWith("did:")) {
		const parts = ctx.split(":");
		const last = parts[parts.length - 1] ?? "";
		return `${parts.slice(0, -1).join(":")}:${last.slice(0, 4)}…`;
	}
	// Raw context IDs (UUIDs etc.) get first…last
	return ctx.slice(0, 8) + "…" + ctx.slice(-4);
}

export function eventsInThread(
	all: StreamEvent[],
	contextId: string,
): StreamEvent[] {
	return all
		.filter((e) => extractContextId(e) === contextId)
		.sort((a, b) => a.ts.localeCompare(b.ts));
}
