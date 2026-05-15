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
 * Pull a usable context id off any event shape:
 * - live status/artifact events carry it on payload.context_id (from JSON
 *   raw); we keep a flattened copy on counterparty for the prototype.
 * - mock events don't have a context_id field; we synthesize one from
 *   counterparty.did so the mock scenario still groups into one thread.
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
	// Mock fallback: per-counterparty grouping
	if (e.counterparty?.did) return `mock:${e.counterparty.did}`;
	return null;
}

export function shortContextId(ctx: string): string {
	if (ctx.length <= 12) return ctx;
	if (ctx.startsWith("mock:")) return ctx.slice(5, 17) + "…";
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
