import { create } from "zustand";
import type { Agent, AgentRole, DetailTab, StreamEvent } from "~/types";
import { agents as seedAgents } from "~/data/mock";

export type TrustPolicy =
	| "fully-supervised"
	| "policy-driven"
	| "fully-autonomous";

export interface NewAgentDraft {
	name: string;
	role: AgentRole;
	did: string;
	trustPolicy: TrustPolicy;
}

export interface Draft {
	id: string;
	agentId: string;
	text: string;
	contextId?: string;
	savedAt: string;
}

interface UIState {
	selectedEventId: string | null;
	selectedThreadId: string | null;
	detailTab: DetailTab;
	showRegister: boolean;
	showCompose: boolean;
	agents: Agent[];
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
	openRegister: () => void;
	closeRegister: () => void;
	openCompose: () => void;
	closeCompose: () => void;
	registerAgent: (draft: NewAgentDraft) => Agent;
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
}

const DRAFTS_LS_KEY = "bindu-comms:drafts";

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
		return arr.filter(
			(d): d is Draft =>
				!!d &&
				typeof (d as Draft).id === "string" &&
				typeof (d as Draft).agentId === "string" &&
				typeof (d as Draft).text === "string",
		);
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
	selectedEventId: "wa-7",
	selectedThreadId: null,
	detailTab: "glance",
	showRegister: false,
	showCompose: false,
	agents: seedAgents,
	liveEvents: [],
	readOverrides: new Set(),
	unreadOverrides: new Set(),
	archivedThreads: new Set(),
	drafts: loadDrafts(),
	composeDraftId: null,
	showDetailRail: false,

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
	openRegister: () => set({ showRegister: true }),
	closeRegister: () => set({ showRegister: false }),
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
	registerAgent: (draft) => {
		const id = draft.name
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, "-")
			.replace(/(^-|-$)/g, "")
			|| `agent-${Math.random().toString(36).slice(2, 6)}`;
		const newAgent: Agent = {
			id,
			name: draft.name,
			did: draft.did,
			role: draft.role,
		};
		set((s) => ({ agents: [...s.agents, newAgent], showRegister: false }));
		return newAgent;
	},
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
		set((s) => {
			const agents = s.agents.find((a) => a.id === e.agentId)
				? s.agents
				: [
						...s.agents,
						{
							id: e.agentId,
							name: e.agentId,
							did: `did:bindu:?:${e.agentId}`,
							role: "agent" as const,
						},
					];
			return { liveEvents: [e, ...s.liveEvents].slice(0, 500), agents };
		}),
}));
