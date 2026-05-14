import type { EventKind, EventState, StreamEvent } from "~/types";

interface RawWebhook {
	id: string;
	agentId: string;
	receivedAt: string;
	payload: {
		event_id?: string;
		sequence?: number;
		timestamp?: string;
		kind?: "status-update" | "artifact-update" | "gateway-event" | string;
		task_id?: string;
		context_id?: string;
		status?: { state?: string };
		artifact?: unknown;
		final?: boolean;
		// gateway-event extras
		event_type?: string;
		parent_id?: string;
		properties?: Record<string, unknown>;
	};
}

// Track per-agent context_ids so the first sighting of a context renders as
// first-contact instead of just another state-change.
const seenContexts = new Map<string, Set<string>>();

function markContext(agentId: string, contextId: string | undefined): boolean {
	if (!contextId) return false;
	let set = seenContexts.get(agentId);
	if (!set) {
		set = new Set();
		seenContexts.set(agentId, set);
	}
	if (set.has(contextId)) return false;
	set.add(contextId);
	return true;
}

const ATTENTION_STATES = new Set<EventState>([
	"input-required",
	"payment-required",
	"auth-required",
]);

const ACTION_FOR_STATE: Record<string, StreamEvent["action"]> = {
	"input-required": { kind: "input", label: "Provide Input" },
	"payment-required": { kind: "pay", label: "Pay" },
	"auth-required": { kind: "approve", label: "Authorize" },
};

const KNOWN_STATES = new Set<EventState>([
	"submitted",
	"pending",
	"working",
	"input-required",
	"payment-required",
	"auth-required",
	"completed",
	"failed",
]);

function normalizeState(raw: string | undefined, isArtifact: boolean): EventState | undefined {
	if (isArtifact) return "completed";
	if (!raw) return undefined;
	return KNOWN_STATES.has(raw as EventState) ? (raw as EventState) : undefined;
}

function mapGatewayEvent(raw: RawWebhook): StreamEvent {
	const p = raw.payload;
	const props = p.properties ?? {};
	const eventType = p.event_type ?? "";
	const tool = String(props.tool ?? "");
	const error = props.error ? String(props.error) : undefined;

	let kind: EventKind = "state-change";
	let state: EventState | undefined;
	let summary: string;
	let counterpartyName = tool || "planner";

	if (eventType === "session.prompt.started") {
		kind = "plan-step";
		state = "working";
		summary = "Plan started";
		counterpartyName = "planner";
	} else if (eventType === "session.prompt.tool.start") {
		kind = "state-change";
		state = "working";
		summary = `→ ${tool || "tool"} call`;
	} else if (eventType === "session.prompt.tool.end") {
		if (error) {
			kind = "state-change";
			state = "failed";
			summary = `${tool || "tool"} failed: ${error.slice(0, 80)}`;
		} else {
			kind = "artifact";
			state = "completed";
			summary = `${tool || "tool"} returned`;
		}
	} else if (eventType === "session.prompt.finished") {
		kind = "state-change";
		state = "completed";
		const stop = props.stopReason ? ` · ${props.stopReason}` : "";
		summary = `Plan finished${stop}`;
		counterpartyName = "planner";
	} else {
		summary = eventType || "(gateway event)";
	}

	const sigs = (props.signatures as Record<string, unknown> | null | undefined) ?? null;
	const signed = !!sigs && (sigs.signed as number) > 0;

	return {
		id: raw.id,
		agentId: raw.agentId,
		parentId: p.parent_id || undefined,
		ts: (p.timestamp ?? raw.receivedAt).slice(11, 19),
		relTs: "live",
		counterparty: {
			name: counterpartyName,
			did: `did:bindu:gateway:${String(props.sessionID ?? "?").slice(0, 8)}`,
			trust: "self",
		},
		kind,
		state,
		summary,
		signed,
		verify: {
			signature: signed,
			didMatch: signed,
			nonce: String(props.callID ?? p.event_id ?? "").slice(0, 8) || "—",
		},
		payload: JSON.stringify(p, null, 2),
	};
}

export function mapWebhookToEvent(raw: RawWebhook): StreamEvent {
	const p = raw.payload;

	if (p.kind === "gateway-event") return mapGatewayEvent(raw);

	const isArtifact = p.kind === "artifact-update";
	const state = normalizeState(p.status?.state, isArtifact);
	const firstContact = !isArtifact && markContext(raw.agentId, p.context_id);

	let kind: EventKind;
	if (isArtifact) kind = "artifact";
	else if (firstContact) kind = "first-contact";
	else kind = "state-change";

	const taskShort = p.task_id?.slice(0, 8) ?? "task";
	const summary = isArtifact
		? "Artifact delivered"
		: firstContact
			? `New task · ${taskShort}`
			: state === "completed"
				? `Completed${p.final ? " · final" : ""}`
				: state === "failed"
					? "Failed"
					: state
						? `state → ${state}${p.final ? " · final" : ""}`
						: "(unknown state)";

	return {
		id: raw.id,
		agentId: raw.agentId,
		ts: (p.timestamp ?? raw.receivedAt).slice(11, 19),
		relTs: "live",
		counterparty: {
			name: taskShort,
			did: `did:bindu:task:${p.task_id ?? "?"}`,
			trust: firstContact ? "new" : "known",
		},
		kind,
		state,
		summary,
		needsAttention: state ? ATTENTION_STATES.has(state) || undefined : undefined,
		action: state ? ACTION_FOR_STATE[state] : undefined,
		signed: true,
		verify: {
			signature: true,
			didMatch: true,
			nonce: (p.event_id ?? "").slice(0, 8) || "—",
		},
		payload: JSON.stringify(p, null, 2),
	};
}
