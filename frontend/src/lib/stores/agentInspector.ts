import { writable } from "svelte/store";

export type ClearHandler = (() => void | Promise<void>) | undefined;

export interface AgentInspectorSnapshot {
	agentName: string | null;
	contextId: string | null;
	sessionId: string | null;
	taskCount: number;
	disabled: boolean;
	onClearContext: ClearHandler;
	onClearTasks: ClearHandler;
}

export const DEFAULT_AGENT_INSPECTOR: AgentInspectorSnapshot = {
	agentName: null,
	contextId: null,
	sessionId: null,
	taskCount: 0,
	disabled: false,
	onClearContext: undefined,
	onClearTasks: undefined,
};

export const agentInspector = writable<AgentInspectorSnapshot>(DEFAULT_AGENT_INSPECTOR);

export function resetAgentInspector() {
	agentInspector.set(DEFAULT_AGENT_INSPECTOR);
}

