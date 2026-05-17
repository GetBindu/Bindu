import { useUI } from "~/state";
import type { StreamEvent } from "~/types";

/** All visible events — currently just the live SSE buffer.
 *
 * Three components (`StreamPanel`, `DetailRail`, `ThreadView`) used to
 * open-code this spread, plus a seed-mock concat that's now gone. Kept
 * as a hook so future sources (server-backfill paginate, search, …)
 * have one place to land. */
export function useAllEvents(): StreamEvent[] {
	return useUI((s) => s.liveEvents);
}
