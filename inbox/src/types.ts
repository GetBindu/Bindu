export type TrustLevel = "self" | "trusted" | "known" | "new" | "untrusted";

export type EventState =
	| "submitted"
	| "pending"
	| "working"
	| "input-required"
	| "payment-required"
	| "auth-required"
	| "completed"
	| "failed";

export type EventKind =
	| "first-contact"
	| "negotiation"
	| "payment"
	| "state-change"
	| "artifact"
	| "human-action"
	| "plan-step"
	| "heartbeat";

export interface Counterparty {
	name: string;
	did: string;
	trust: TrustLevel;
}

export interface StreamEvent {
	id: string;
	agentId: string;
	ts: string;
	relTs: string;
	/** Full ISO datetime (`2026-05-14T22:42:11.614Z`) when known.
	 * Used for Gmail-style "3:47 PM / Mon / May 14" date rendering.
	 * Mock events leave it undefined and the renderer falls back to relTs. */
	at?: string;
	counterparty: Counterparty;
	kind: EventKind;
	state?: EventState;
	summary: string;
	needsAttention?: boolean;
	action?: { kind: "approve" | "pay" | "input"; label: string };
	signed: boolean;
	verify: { signature: boolean; didMatch: boolean; nonce: string };
	/** Full message body, rendered inline in the thread view. Populated for
	 * outbound sends (the operator's typed text) and artifact-update events
	 * (the agent's response text extracted from `artifact.parts[].text`).
	 * Other event kinds — lifecycle, state-change, plan-step — leave this
	 * undefined and fall back to the one-line summary. */
	body?: string;
	/** Pretty-printed JSON of the source payload, kept for the Inspect tab. */
	payload?: string;
	/** Parsed payload object — populated at SSE-ingest so downstream code
	 * (thread grouping, search, subject derivation) doesn't re-`JSON.parse`
	 * the same string five times per render. */
	payloadJson?: Record<string, unknown>;
}

export type DetailTab = "glance" | "verify" | "inspect";
