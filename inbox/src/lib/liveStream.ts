import type { EventKind, EventState, StreamEvent } from "~/types";

interface RawWebhook {
	id: string;
	agentId: string;
	receivedAt: string;
	/** Server-tracked: true the first time this context_id was seen for the agent. */
	firstContact?: boolean;
	payload: {
		event_id?: string;
		sequence?: number;
		timestamp?: string;
		kind?:
			| "status-update"
			| "artifact-update"
			| "gateway-event"
			| "task-started"
			| "task-artifact"
			| "task-finished"
			| "plan-reply"
			| "plan-summary"
			| string;
		task_id?: string;
		context_id?: string;
		status?: { state?: string; message?: unknown };
		artifact?: unknown;
		final?: boolean;
		// `status.message` carries the agent's prompt on intermediate
		// states (input-required, payment-required, auth-required).
		// Same A2A Message shape as artifact.parts — the mapper reuses
		// the same extractor.
		// gateway-event extras
		event_type?: string;
		parent_id?: string;
		properties?: Record<string, unknown>;
		// outbound (operator-sent) extras
		direction?: "in" | "out";
		from_did?: string;
		to_agent_id?: string;
		to_did?: string | null;
		message_id?: string;
		text?: string;
		upstream_status?: number;
		upstream_error?: string | null;
		// gateway plan-trace extras (synthesized by /api/plan from the
		// gateway's SSE stream — task.started / task.artifact /
		// task.finished / compaction-summary / final answer).
		agent?: string;
		agent_did?: string | null;
		skill?: string;
		input?: unknown;
		content?: string | null;
		title?: string | null;
		state?: string;
		error?: string | null;
	};
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

/** Pull the HH:MM:SS slice out of `payload.timestamp` (ISO8601), falling
 * back to the receiver's wall-clock when the upstream didn't carry one.
 * Three mappers used to inline this; one helper keeps them in sync. */
function pickTs(raw: RawWebhook): { hms: string; iso: string } {
	const iso = raw.payload.timestamp ?? raw.receivedAt;
	return { hms: iso.slice(11, 19), iso };
}

function mapOutboundEvent(raw: RawWebhook): StreamEvent {
	const p = raw.payload;
	const upstreamOk =
		!p.upstream_error && (p.upstream_status ?? 0) >= 200 && (p.upstream_status ?? 0) < 300;
	const fullText = p.text ?? "";
	const summary = p.upstream_error
		? `Send failed: ${p.upstream_error.slice(0, 80)}`
		: `“${fullText.slice(0, 120)}”`;
	const { hms, iso } = pickTs(raw);
	return {
		id: raw.id,
		agentId: raw.agentId,
		ts: hms,
		relTs: "just now",
		at: iso,
		counterparty: {
			name: p.to_agent_id ?? "agent",
			did: p.to_did ?? `did:bindu:?:${p.to_agent_id ?? "?"}`,
			trust: "known",
		},
		kind: "human-action",
		state: upstreamOk ? "submitted" : p.upstream_error ? "failed" : "pending",
		summary,
		body: p.upstream_error ? undefined : fullText || undefined,
		signed: false,
		verify: {
			signature: false,
			didMatch: false,
			nonce: (p.message_id ?? "").slice(0, 8) || "—",
		},
		payload: JSON.stringify(p, null, 2),
		payloadJson: p as Record<string, unknown>,
	};
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

	const { hms, iso } = pickTs(raw);
	return {
		id: raw.id,
		agentId: raw.agentId,
		ts: hms,
		relTs: "live",
		at: iso,
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
		payloadJson: p as Record<string, unknown>,
	};
}

/** Pull human-readable text out of any A2A container that carries a
 * `parts` array — works on both artifacts and status messages, which
 * share the same Message shape. Only `kind: "text"` entries
 * contribute; file/data parts are skipped (no inline viewer yet).
 * Returns undefined when there's nothing to show, so the row falls
 * back to its one-line summary. */
function extractTextParts(container: unknown): string | undefined {
	if (!container || typeof container !== "object") return undefined;
	const parts = (container as { parts?: unknown }).parts;
	if (!Array.isArray(parts)) return undefined;
	const texts: string[] = [];
	for (const part of parts) {
		if (!part || typeof part !== "object") continue;
		const kind = (part as { kind?: unknown }).kind;
		const text = (part as { text?: unknown }).text;
		if (kind === "text" && typeof text === "string" && text.length > 0) {
			texts.push(text);
		}
	}
	return texts.length > 0 ? texts.join("\n\n") : undefined;
}

// Strip the `<remote_content agent="..." verified="...">…</remote_content>`
// wrapper the gateway puts around peer agent text so the inbox shows the
// raw answer instead of XML noise. Keeps signature/trust info in
// payloadJson for the inspect tab.
function stripRemoteContent(s: string | null | undefined): string | undefined {
	if (!s) return undefined;
	const m = s.match(/<remote_content[^>]*>([\s\S]*?)<\/remote_content>/);
	return (m ? m[1] : s).trim() || undefined;
}

function mapPlanTraceEvent(raw: RawWebhook): StreamEvent {
	const p = raw.payload;
	const { hms, iso } = pickTs(raw);
	const agentName = p.agent ?? "agent";
	const taskShort = (p.task_id ?? "").slice(0, 12) || "task";
	const did =
		p.agent_did && p.agent_did.length > 0
			? p.agent_did
			: `did:bindu:task:${p.task_id ?? "?"}`;

	let kind: EventKind = "state-change";
	let state: EventState | undefined;
	let summary = "";
	let body: string | undefined;
	let counterpartyName = agentName;

	if (p.kind === "task-started") {
		kind = "plan-step";
		state = "working";
		summary = p.skill ? `→ ${agentName} · ${p.skill}` : `→ ${agentName}`;
	} else if (p.kind === "task-artifact") {
		kind = "artifact";
		state = "completed";
		body = stripRemoteContent(p.content);
		summary = p.title || `${agentName} returned`;
	} else if (p.kind === "task-finished") {
		kind = "state-change";
		state = normalizeState(p.state, false);
		const err = p.error ? ` · ${String(p.error).slice(0, 80)}` : "";
		summary = state ? `${agentName} ${state}${err}` : `${agentName} finished${err}`;
	} else if (p.kind === "plan-reply") {
		kind = "artifact";
		state = "completed";
		body = p.text;
		summary = "Plan answer";
		counterpartyName = "planner";
	} else if (p.kind === "plan-summary") {
		kind = "state-change";
		summary = "Compaction summary";
		counterpartyName = "planner";
	}

	return {
		id: raw.id,
		agentId: raw.agentId,
		ts: hms,
		relTs: "live",
		at: iso,
		counterparty: {
			name: counterpartyName,
			did,
			trust: p.kind === "plan-reply" || p.kind === "plan-summary" ? "self" : "known",
		},
		kind,
		state,
		summary,
		body,
		signed: false,
		verify: {
			signature: false,
			didMatch: false,
			nonce: (p.event_id ?? "").slice(0, 8) || taskShort,
		},
		payload: JSON.stringify(p, null, 2),
		payloadJson: p as Record<string, unknown>,
	};
}

const PLAN_TRACE_KINDS = new Set([
	"task-started",
	"task-artifact",
	"task-finished",
	"plan-reply",
	"plan-summary",
]);

export function mapWebhookToEvent(raw: RawWebhook): StreamEvent {
	const p = raw.payload;

	if (p.kind === "gateway-event") return mapGatewayEvent(raw);
	if (p.kind === "outbound") return mapOutboundEvent(raw);
	if (p.kind && PLAN_TRACE_KINDS.has(p.kind)) return mapPlanTraceEvent(raw);

	const isArtifact = p.kind === "artifact-update";
	const state = normalizeState(p.status?.state, isArtifact);
	const firstContact = !isArtifact && (raw.firstContact ?? false);
	// Body precedence: artifact text on artifact-update events (the
	// final answer), else the status.message text on status-update
	// events (the agent's prompt on input-required / payment-required
	// / auth-required, when the core forwards it).
	const body = isArtifact
		? extractTextParts(p.artifact)
		: extractTextParts(p.status?.message);

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

	// Lifecycle + artifact events from push_manager don't carry signature
	// material in the payload itself — they're transport-authenticated by
	// the webhook URL/token, not cryptographically signed. Mark honestly
	// as unsigned. Real Ed25519 verification of artifact bodies is a
	// future change.
	const { hms, iso } = pickTs(raw);
	return {
		id: raw.id,
		agentId: raw.agentId,
		ts: hms,
		relTs: "live",
		at: iso,
		counterparty: {
			name: taskShort,
			did: `did:bindu:task:${p.task_id ?? "?"}`,
			trust: firstContact ? "new" : "known",
		},
		kind,
		state,
		summary,
		body,
		needsAttention: state ? ATTENTION_STATES.has(state) || undefined : undefined,
		action: state ? ACTION_FOR_STATE[state] : undefined,
		signed: false,
		verify: {
			signature: false,
			didMatch: false,
			nonce: (p.event_id ?? "").slice(0, 8) || "—",
		},
		payload: JSON.stringify(p, null, 2),
		payloadJson: p as Record<string, unknown>,
	};
}
