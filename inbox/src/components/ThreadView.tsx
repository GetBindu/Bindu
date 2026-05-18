import { useMemo, useState } from "react";
import clsx from "clsx";
import { ArrowLeftIcon, PaperPlaneTiltIcon } from "@phosphor-icons/react";
import { useUI } from "~/state";
import { eventsInThread, shortContextId } from "~/lib/threads";
import { EventRow } from "./EventRow";
import { useAllEvents } from "~/lib/hooks";
import { postJson } from "~/lib/fetch";
import { postSse } from "~/lib/sse";
import { OUTBOX_AGENT_ID } from "~/lib/constants";
import type { StreamEvent } from "~/types";

interface Props {
	contextId: string;
}

/**
 * One thread's events, oldest → newest. Spans all agents (live + mock)
 * so the user sees one conversation instead of two half-conversations
 * across lanes (Step 3 stitching).
 *
 * The composer at the bottom posts a reply on the existing context_id,
 * so the conversation extends instead of forking a new thread.
 */
export function ThreadView({ contextId }: Props) {
	const selectThread = useUI((s) => s.selectThread);
	const allEvents = useAllEvents();
	const ordered = useMemo(
		() => eventsInThread(allEvents, contextId),
		[allEvents, contextId],
	);
	const first = ordered[0];
	const counterpartyName = first?.counterparty.name ?? "—";
	const agentLanes = Array.from(new Set(ordered.map((e) => e.agentId)));

	// Derive the full recipient set for replies. When the thread was
	// originally a multi-agent compose, every reply should fan back out
	// to the same roster — otherwise turn 2 sticks to whichever agent
	// happened to answer first (the bug seen in the math+joke log: the
	// user asked "now write a joke with the result" and the inbox sent
	// it back to math_agent only, who correctly refused). The planner
	// re-evaluates per turn against the full roster, so we hand it the
	// whole set and let it pick.
	const replyRecipients = useMemo(
		() => deriveReplyRecipients(ordered),
		[ordered],
	);

	return (
		<>
			<div className="flex items-center gap-2 border-b border-(--color-border-soft) bg-white px-6 py-2.5">
				<button
					type="button"
					onClick={() => selectThread(null)}
					className="flex items-center gap-1 rounded-md border border-(--color-border-soft) bg-white px-2 py-1 text-[11px] text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
				>
					<ArrowLeftIcon size={11} weight="bold" />
					Inbox
				</button>
				<div className="ml-2 flex min-w-0 flex-1 items-baseline gap-2">
					<h2 className="truncate text-[13px] font-medium text-fg">
						{counterpartyName === "task"
							? `Thread ${shortContextId(contextId)}`
							: counterpartyName}
					</h2>
					<span className="font-mono text-[10px] text-fg-dim">
						{shortContextId(contextId)}
					</span>
				</div>
				<div className="flex items-center gap-2 text-[10px] text-fg-dim">
					{agentLanes.length > 1 && (
						<span className="rounded-full border border-(--color-cobalt)/40 bg-(--color-cobalt-soft) px-1.5 py-0.5 text-(--color-cobalt-strong)">
							stitched across {agentLanes.length} lanes
						</span>
					)}
					<span>
						{ordered.length} message{ordered.length === 1 ? "" : "s"}
					</span>
				</div>
			</div>

			<div className="scrollbar flex-1 overflow-y-auto">
				{ordered.length === 0 ? (
					<div className="flex h-40 items-center justify-center text-[12px] text-fg-dim">
						No events in this thread.
					</div>
				) : (
					ordered.map((e) => (
						<EventRow
							key={e.id}
							event={e}
							attentionLane={!!e.needsAttention}
						/>
					))
				)}
			</div>

			<ReplyBox contextId={contextId} recipients={replyRecipients} />
		</>
	);
}

function deriveReplyRecipients(events: StreamEvent[]): string[] {
	// Collect every distinct recipient seen on this thread, preserving
	// insertion order. Two sources contribute:
	//   1. `to_agent_id` from outbound /api/compose events (one peer per
	//      event), and `plan_agents` from `plan-question` events (the
	//      roster of a prior multi-agent compose — recorded verbatim by
	//      inbox/server's /api/plan handler).
	//   2. Any non-outbox lane the thread has lit up. That covers
	//      mock-data threads and any peer that replied without an
	//      explicit outbound first.
	// Without (1)'s `plan_agents`, a multi-agent thread would collapse
	// to a single recipient on first reply — exactly the sticky-routing
	// bug.
	const seen = new Set<string>();
	const out: string[] = [];
	const add = (id: unknown) => {
		if (typeof id !== "string" || id.length === 0) return;
		if (seen.has(id)) return;
		seen.add(id);
		out.push(id);
	};
	for (const e of events) {
		if (e.agentId !== OUTBOX_AGENT_ID) continue;
		add(e.payloadJson?.to_agent_id);
		const planAgents = (e.payloadJson as { plan_agents?: unknown })
			?.plan_agents;
		if (Array.isArray(planAgents)) for (const a of planAgents) add(a);
	}
	for (const e of events) {
		if (e.agentId === OUTBOX_AGENT_ID) continue;
		add(e.agentId);
	}
	return out;
}

function ReplyBox({
	contextId,
	recipients,
}: {
	contextId: string;
	recipients: string[];
}) {
	const [text, setText] = useState("");
	const [status, setStatus] = useState<"idle" | "sending" | "error">("idle");
	const [errMsg, setErrMsg] = useState<string | null>(null);

	if (recipients.length === 0) {
		return (
			<div className="border-t border-(--color-border-soft) bg-slate-50 px-6 py-3 text-[11px] text-fg-dim">
				Replies aren't available for this thread (no agent target identified).
			</div>
		);
	}

	const isMulti = recipients.length >= 2;
	const canSubmit = text.trim().length > 0 && status !== "sending";

	async function handleSend(e: React.FormEvent) {
		e.preventDefault();
		if (!canSubmit) return;
		setStatus("sending");
		setErrMsg(null);

		// Multi-recipient thread → /api/plan. The gateway's planner
		// re-evaluates the roster per turn (verified empirically against
		// the gateway_test_fleet: turn 2 "now tell me a joke about that
		// result" routed to joke alone even with math also in the
		// catalog). Passing `sessionId: contextId` keeps the thread
		// stitched in the inbox; /api/plan also records the question as
		// a `plan-question` outbox event for thread display.
		//
		// We drain the SSE so the connection closes cleanly, but ignore
		// frame-level state — the inbox already shows live progress via
		// webhook ingestion from each peer agent. This keeps ReplyBox
		// thin (no embedded planner UI) and matches its compose-modal
		// counterpart's "fire and let the webhooks paint" behavior.
		if (isMulti) {
			try {
				const res = await postSse(
					"/api/plan",
					{
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							question: text.trim(),
							agentIds: recipients,
							sessionId: contextId,
						}),
					},
					() => {},
				);
				if (!res.ok) {
					const j = (await res.json().catch(() => ({}))) as {
						detail?: string;
						error?: string;
					};
					setStatus("error");
					setErrMsg(j.detail ?? j.error ?? `HTTP ${res.status}`);
					return;
				}
			} catch (err) {
				setStatus("error");
				setErrMsg((err as Error).message);
				return;
			}
			setText("");
			setStatus("idle");
			return;
		}

		// Single-recipient thread → direct A2A.
		const r = await postJson("/api/compose", {
			agentId: recipients[0],
			text: text.trim(),
			contextId,
		});
		if (!r.ok) {
			setStatus("error");
			setErrMsg(r.errMsg);
			return;
		}
		setText("");
		setStatus("idle");
	}

	const replyingTo = isMulti
		? `${recipients.length} agents`
		: recipients[0];

	return (
		<form
			onSubmit={handleSend}
			className="border-t border-(--color-border-soft) bg-white px-6 py-3"
		>
			<div className="mb-1.5 flex items-center justify-between text-[10px] text-fg-dim">
				<span>
					Replying to <span className="text-fg-muted">{replyingTo}</span> on this thread
				</span>
				{status === "error" && errMsg && (
					<span className="text-rose-700">✗ {errMsg}</span>
				)}
			</div>
			<div className="flex items-end gap-2">
				<textarea
					value={text}
					onChange={(e) => setText(e.target.value)}
					onKeyDown={(e) => {
						if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
							handleSend(e as unknown as React.FormEvent);
						}
					}}
					placeholder="Type a reply… (⌘↩ to send)"
					rows={2}
					className="flex-1 resize-none rounded-md border border-(--color-border) bg-white px-3 py-2 text-[13px] text-fg placeholder-fg-faint outline-none transition focus:border-(--color-cobalt) focus:ring-2 focus:ring-(--color-cobalt-soft)"
				/>
				<button
					type="submit"
					disabled={!canSubmit}
					className={clsx(
						"flex items-center gap-1.5 rounded-md px-3 py-2 text-[12px] font-medium shadow-sm transition",
						canSubmit
							? "bg-(--color-cobalt) text-white hover:bg-(--color-cobalt-strong)"
							: "bg-slate-200 text-slate-400",
					)}
				>
					<PaperPlaneTiltIcon size={12} weight="fill" />
					{status === "sending" ? "Sending…" : "Send"}
				</button>
			</div>
		</form>
	);
}
