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

interface UIState {
	selectedEventId: string | null;
	selectedThreadId: string | null;
	detailTab: DetailTab;
	streamPaused: boolean;
	expandedTraces: Set<string>;
	scopeFilter: string | null;
	showRegister: boolean;
	agents: Agent[];
	liveEvents: StreamEvent[];

	selectEvent: (id: string | null) => void;
	selectThread: (contextId: string | null) => void;
	setDetailTab: (tab: DetailTab) => void;
	togglePause: () => void;
	toggleTrace: (id: string) => void;
	setScope: (id: string | null) => void;
	openRegister: () => void;
	closeRegister: () => void;
	registerAgent: (draft: NewAgentDraft) => Agent;
	addLiveEvent: (e: StreamEvent) => void;
}

export const useUI = create<UIState>((set) => ({
	selectedEventId: "wa-7",
	selectedThreadId: null,
	detailTab: "glance",
	streamPaused: false,
	expandedTraces: new Set(["plan-1"]),
	scopeFilter: null,
	showRegister: false,
	agents: seedAgents,
	liveEvents: [],

	selectEvent: (id) => set({ selectedEventId: id }),
	selectThread: (contextId) => set({ selectedThreadId: contextId }),
	setDetailTab: (tab) => set({ detailTab: tab }),
	togglePause: () => set((s) => ({ streamPaused: !s.streamPaused })),
	toggleTrace: (id) =>
		set((s) => {
			const next = new Set(s.expandedTraces);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return { expandedTraces: next };
		}),
	setScope: (id) =>
		set((s) => ({ scopeFilter: s.scopeFilter === id ? null : id })),
	openRegister: () => set({ showRegister: true }),
	closeRegister: () => set({ showRegister: false }),
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
			unread: 0,
			needsAttention: 0,
			role: draft.role,
		};
		set((s) => ({ agents: [...s.agents, newAgent], showRegister: false }));
		return newAgent;
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
							unread: 0,
							needsAttention: 0,
							role: "agent" as const,
						},
					];
			return { liveEvents: [e, ...s.liveEvents].slice(0, 500), agents };
		}),
}));
