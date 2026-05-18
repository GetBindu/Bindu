import { create } from "zustand";
import type { DetailTab, StreamEvent } from "~/types";
import type { PersonalAgent } from "~/lib/api-types";

export interface Draft {
	id: string;
	/** Recipients the draft is addressed to. Multi-recipient drafts were
	 * previously collapsed to a single `agentId: string` field, which
	 * broke the inbox's multi-agent compose flow when a draft was
	 * resubmitted (the operator picked N agents, saved, reopened, and
	 * only the first one was reloaded). `loadDrafts` migrates legacy
	 * entries in-place so old localStorage payloads keep working. */
	agentIds: string[];
	text: string;
	contextId?: string;
	savedAt: string;
}

interface UIState {
	selectedEventId: string | null;
	selectedThreadId: string | null;
	detailTab: DetailTab;
	showCompose: boolean;
	liveEvents: StreamEvent[];
	/** ctx ids the user has explicitly marked read */
	readOverrides: Set<string>;
	/** ctx ids the user has explicitly marked unread (overrides everything) */
	unreadOverrides: Set<string>;
	/** ctx ids the user has archived (hidden from inbox/sent, visible in archive folder) */
	archivedThreads: Set<string>;
	drafts: Draft[];

	selectEvent: (id: string | null) => void;
	selectThread: (contextId: string | null) => void;
	setDetailTab: (tab: DetailTab) => void;
	openCompose: () => void;
	closeCompose: () => void;
	addLiveEvent: (e: StreamEvent) => void;
	markRead: (contextId: string) => void;
	markUnread: (contextId: string) => void;
	archiveThread: (contextId: string) => void;
	unarchiveThread: (contextId: string) => void;
	saveDraft: (draft: Draft) => void;
	deleteDraft: (id: string) => void;
	composeDraftId: string | null;
	openComposeWith: (draftId: string | null) => void;
	hydrateThreadState: () => Promise<void>;
	/** Auditor side panel (Verify / Inspect) toggle. Off by default so the
	 * inbox surface stays Gmail-shape. */
	showDetailRail: boolean;
	toggleDetailRail: () => void;

	// --- personal agent --------------------------------------------------
	/** Operator's own bindufied agent. `null` = not yet onboarded; the
	 * wizard takes over the screen when this is null. `undefined` = we
	 * haven't fetched /api/me yet (still bootstrapping). */
	me: PersonalAgent | null | undefined;
	hydrateMe: () => Promise<void>;
	setMe: (m: PersonalAgent | null) => void;
	/** True while the first-run wizard is open. Persists across the
	 * three steps so the user can navigate back without losing the
	 * persona draft. */
	wizardOpen: boolean;
	openWizard: () => void;
	closeWizard: () => void;
}

const DRAFTS_LS_KEY = "bindu-comms:drafts";

/** Soft cap on the in-memory event ring buffer. Older events fall off
 * silently when the buffer fills — the server keeps the full history,
 * so refreshing the page rehydrates from `/api/events/...`. 500 is
 * roughly two days of dev-fleet traffic; raise it if you start losing
 * threads on long-running sessions. */
export const LIVE_EVENTS_CAP = 500;

interface ThreadStateRow {
	contextId: string;
	readAt: string | null;
	unreadAt: string | null;
	archivedAt: string | null;
}

function postThreadAction(
	contextId: string,
	action: "read" | "unread" | "archive" | "unarchive",
): void {
	// Fire-and-forget — local state already updated optimistically.
	void fetch(
		`/api/threads/${encodeURIComponent(contextId)}/${action}`,
		{ method: "POST" },
	).catch(() => {
		// Server unreachable: optimistic local state stays; next hydrate
		// will reconcile. Logging only for dev visibility.
		// eslint-disable-next-line no-console
		console.warn(`[thread-state] ${action} failed to sync for ${contextId}`);
	});
}

function loadDrafts(): Draft[] {
	if (typeof window === "undefined") return [];
	try {
		const raw = window.localStorage.getItem(DRAFTS_LS_KEY);
		if (!raw) return [];
		const arr = JSON.parse(raw) as unknown;
		if (!Array.isArray(arr)) return [];
		const out: Draft[] = [];
		for (const d of arr) {
			if (!d || typeof d !== "object") continue;
			const row = d as Record<string, unknown>;
			if (typeof row.id !== "string" || typeof row.text !== "string") continue;
			// Migrate legacy single-recipient drafts (agentId: string) to the
			// multi-recipient shape (agentIds: string[]). Without this, a
			// user with an old draft in localStorage would lose it on first
			// reload after upgrading.
			let agentIds: string[];
			if (Array.isArray(row.agentIds)) {
				agentIds = (row.agentIds as unknown[]).filter(
					(v): v is string => typeof v === "string" && v.length > 0,
				);
			} else if (typeof row.agentId === "string" && row.agentId.length > 0) {
				agentIds = [row.agentId];
			} else {
				continue;
			}
			if (agentIds.length === 0) continue;
			out.push({
				id: row.id,
				agentIds,
				text: row.text,
				contextId:
					typeof row.contextId === "string" ? row.contextId : undefined,
				savedAt: typeof row.savedAt === "string" ? row.savedAt : "",
			});
		}
		return out;
	} catch {
		return [];
	}
}

function saveDrafts(drafts: Draft[]): void {
	if (typeof window === "undefined") return;
	try {
		window.localStorage.setItem(DRAFTS_LS_KEY, JSON.stringify(drafts));
	} catch {
		// no-op
	}
}

export const useUI = create<UIState>((set) => ({
	selectedEventId: null,
	selectedThreadId: null,
	detailTab: "glance",
	showCompose: false,
	liveEvents: [],
	readOverrides: new Set(),
	unreadOverrides: new Set(),
	archivedThreads: new Set(),
	drafts: loadDrafts(),
	composeDraftId: null,
	showDetailRail: false,

	me: undefined,
	hydrateMe: async () => {
		try {
			const r = await fetch("/api/me");
			if (!r.ok) {
				set({ me: null });
				return;
			}
			const j = (await r.json()) as PersonalAgent | null;
			set({ me: j });
		} catch {
			set({ me: null });
		}
	},
	setMe: (m) => set({ me: m }),
	wizardOpen: false,
	openWizard: () => set({ wizardOpen: true }),
	closeWizard: () => set({ wizardOpen: false }),

	selectEvent: (id) => set({ selectedEventId: id }),
	toggleDetailRail: () => set((s) => ({ showDetailRail: !s.showDetailRail })),
	selectThread: (contextId) =>
		set((s) => {
			// Opening a thread implicitly marks it read.
			if (!contextId) return { selectedThreadId: null };
			const read = new Set(s.readOverrides);
			const unread = new Set(s.unreadOverrides);
			read.add(contextId);
			unread.delete(contextId);
			postThreadAction(contextId, "read");
			return {
				selectedThreadId: contextId,
				readOverrides: read,
				unreadOverrides: unread,
			};
		}),
	setDetailTab: (tab) => set({ detailTab: tab }),
	openCompose: () => set({ showCompose: true, composeDraftId: null }),
	closeCompose: () => set({ showCompose: false, composeDraftId: null }),
	openComposeWith: (draftId) =>
		set({ showCompose: true, composeDraftId: draftId }),
	saveDraft: (draft) =>
		set((s) => {
			const next = [draft, ...s.drafts.filter((d) => d.id !== draft.id)];
			saveDrafts(next);
			return { drafts: next };
		}),
	deleteDraft: (id) =>
		set((s) => {
			const next = s.drafts.filter((d) => d.id !== id);
			saveDrafts(next);
			return { drafts: next };
		}),
	markRead: (contextId) =>
		set((s) => {
			const read = new Set(s.readOverrides);
			const unread = new Set(s.unreadOverrides);
			read.add(contextId);
			unread.delete(contextId);
			postThreadAction(contextId, "read");
			return { readOverrides: read, unreadOverrides: unread };
		}),
	markUnread: (contextId) =>
		set((s) => {
			const read = new Set(s.readOverrides);
			const unread = new Set(s.unreadOverrides);
			read.delete(contextId);
			unread.add(contextId);
			postThreadAction(contextId, "unread");
			return { readOverrides: read, unreadOverrides: unread };
		}),
	archiveThread: (contextId) =>
		set((s) => {
			const archived = new Set(s.archivedThreads);
			archived.add(contextId);
			postThreadAction(contextId, "archive");
			// Closing the thread on archive matches Gmail UX: the row disappears
			// from the visible folder and the panel collapses.
			return {
				archivedThreads: archived,
				selectedThreadId:
					s.selectedThreadId === contextId ? null : s.selectedThreadId,
			};
		}),
	unarchiveThread: (contextId) =>
		set((s) => {
			const archived = new Set(s.archivedThreads);
			archived.delete(contextId);
			postThreadAction(contextId, "unarchive");
			return { archivedThreads: archived };
		}),
	hydrateThreadState: async () => {
		try {
			const r = await fetch("/api/threads/state");
			if (!r.ok) return;
			const rows = (await r.json()) as ThreadStateRow[];
			const read = new Set<string>();
			const unread = new Set<string>();
			const archived = new Set<string>();
			for (const row of rows) {
				if (row.archivedAt) archived.add(row.contextId);
				if (row.unreadAt && !row.readAt) unread.add(row.contextId);
				else if (row.readAt) read.add(row.contextId);
			}
			set({
				readOverrides: read,
				unreadOverrides: unread,
				archivedThreads: archived,
			});
		} catch {
			// server unreachable — keep whatever the local optimistic state was
		}
	},
	addLiveEvent: (e) =>
		set((s) => ({ liveEvents: [e, ...s.liveEvents].slice(0, LIVE_EVENTS_CAP) })),
}));
