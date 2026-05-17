import type { EventKind, EventState, TrustLevel } from "~/types";

/** Shorten a DID for display by truncating its trailing segment.
 *
 * `tailChars` controls how many characters of the last colon-segment
 * survive — defaults to 6 for general DID rendering; thread-key short
 * IDs use 4 (see {@link shortContextId}). */
export function shortDid(did: string, tailChars = 6): string {
	if (did.length <= 28) return did;
	const parts = did.split(":");
	const last = parts[parts.length - 1] ?? "";
	return parts.slice(0, -1).join(":") + ":" + last.slice(0, tailChars) + "…";
}

/** Normalise a free-form name into a URL/agent-id-safe slug.
 *
 * Used wherever the UI mints an id from a human-readable name. Falls
 * back to a short random id when the input slugs to empty.
 *
 * We preserve underscores because agno-style agent names (joke_agent,
 * math_agent, bindu_docs_agent) arrive on the webhook path verbatim —
 * `POST /webhooks/bindu/joke_agent` — so if the manual-add slug
 * collapsed them to `joke-agent` we'd end up with two Contacts rows
 * for the same agent the moment a webhook fires. */
export function slugify(name: string, fallbackPrefix = "agent"): string {
	const slug = name
		.toLowerCase()
		.replace(/[^a-z0-9_]+/g, "-")
		.replace(/(^-|-$)/g, "");
	return slug || `${fallbackPrefix}-${Math.random().toString(36).slice(2, 6)}`;
}

export const trustMeta: Record<
	TrustLevel,
	{ label: string; color: string; bg: string; border: string }
> = {
	self: {
		label: "you",
		color: "text-slate-600",
		bg: "bg-slate-100",
		border: "border-slate-200",
	},
	trusted: {
		label: "trusted",
		color: "text-(--color-cobalt)",
		bg: "bg-(--color-cobalt-soft)",
		border: "border-(--color-cobalt-soft)",
	},
	known: {
		label: "known",
		color: "text-blue-800",
		bg: "bg-blue-50",
		border: "border-blue-200",
	},
	new: {
		label: "first-contact",
		color: "text-yellow-800",
		bg: "bg-yellow-50",
		border: "border-yellow-300",
	},
	untrusted: {
		label: "untrusted",
		color: "text-rose-700",
		bg: "bg-rose-50",
		border: "border-rose-200",
	},
};

export const stateMeta: Record<
	EventState,
	{ color: string; bg: string; border: string }
> = {
	submitted: {
		color: "text-slate-700",
		bg: "bg-slate-100",
		border: "border-slate-300",
	},
	pending: {
		color: "text-slate-600",
		bg: "bg-slate-100",
		border: "border-slate-200",
	},
	working: {
		color: "text-blue-800",
		bg: "bg-blue-50",
		border: "border-blue-200",
	},
	"input-required": {
		color: "text-yellow-800",
		bg: "bg-yellow-50",
		border: "border-yellow-300",
	},
	"payment-required": {
		color: "text-blue-900",
		bg: "bg-blue-100",
		border: "border-blue-300",
	},
	"auth-required": {
		color: "text-yellow-900",
		bg: "bg-yellow-100",
		border: "border-yellow-400",
	},
	completed: {
		color: "text-(--color-cobalt)",
		bg: "bg-(--color-cobalt-soft)",
		border: "border-(--color-cobalt-soft)",
	},
	failed: {
		color: "text-rose-700",
		bg: "bg-rose-50",
		border: "border-rose-200",
	},
};

/**
 * Gmail-shape compact date for thread rows.
 *
 *   today      → "3:47 PM"
 *   yesterday  → "Yesterday"
 *   this week  → "Mon"
 *   this year  → "May 14"
 *   older      → "5/14/24"
 *
 * Returns the fallback string when the ISO can't be parsed, so mock data
 * without `at` still renders something.
 */
export function formatListDate(iso?: string, fallback = ""): string {
	if (!iso) return fallback;
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return fallback || iso;
	const now = new Date();

	const sameDay = d.toDateString() === now.toDateString();
	if (sameDay) {
		return d.toLocaleTimeString(undefined, {
			hour: "numeric",
			minute: "2-digit",
		});
	}

	const yesterday = new Date(now);
	yesterday.setDate(now.getDate() - 1);
	if (d.toDateString() === yesterday.toDateString()) return "Yesterday";

	const daysDiff = Math.floor(
		(now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24),
	);
	if (daysDiff < 7 && daysDiff >= 0) {
		return d.toLocaleDateString(undefined, { weekday: "short" });
	}

	if (d.getFullYear() === now.getFullYear()) {
		return d.toLocaleDateString(undefined, {
			month: "short",
			day: "numeric",
		});
	}

	return d.toLocaleDateString(undefined, {
		month: "numeric",
		day: "numeric",
		year: "2-digit",
	});
}

export const kindGlyph: Record<EventKind, string> = {
	"first-contact": "✦",
	negotiation: "⇄",
	payment: "₿",
	"state-change": "→",
	artifact: "✓",
	"human-action": "●",
	"plan-step": "▶",
	heartbeat: "·",
};
