import { useMemo, useState } from "react";
import clsx from "clsx";
import { ArrowLeftIcon, PaperPlaneTiltIcon } from "@phosphor-icons/react";
import { useUI } from "~/state";
import { eventsInThread, shortContextId } from "~/lib/threads";
import { EventRow } from "./EventRow";
import { useAllEvents } from "~/lib/hooks";
import { postJson } from "~/lib/fetch";
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

	// Derive the target agent for the reply: prefer the recipient declared
	// on an outbound event (operator-canonical), else the first non-outbox
	// lane (the agent processing this context). Mock-data threads have no
	// outbound + no non-outbox lane events to draw from — replies stay
	// disabled in that case.
	const replyTarget = useMemo(() => deriveReplyTarget(ordered), [ordered]);

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

			<ReplyBox contextId={contextId} target={replyTarget} />
		</>
	);
}

function deriveReplyTarget(events: StreamEvent[]): string | null {
	// First preference: an outbound event with to_agent_id field.
	for (const e of events) {
		if (e.agentId !== OUTBOX_AGENT_ID) continue;
		const to = e.payloadJson?.to_agent_id;
		if (typeof to === "string" && to.length > 0) return to;
	}
	// Fallback: the first non-outbox lane is the agent processing this thread.
	for (const e of events) {
		if (e.agentId !== OUTBOX_AGENT_ID) return e.agentId;
	}
	return null;
}

function ReplyBox({
	contextId,
	target,
}: {
	contextId: string;
	target: string | null;
}) {
	const [text, setText] = useState("");
	const [status, setStatus] = useState<"idle" | "sending" | "error">("idle");
	const [errMsg, setErrMsg] = useState<string | null>(null);

	if (!target) {
		return (
			<div className="border-t border-(--color-border-soft) bg-slate-50 px-6 py-3 text-[11px] text-fg-dim">
				Replies aren't available for this thread (no agent target identified).
			</div>
		);
	}

	const canSubmit = text.trim().length > 0 && status !== "sending";

	async function handleSend(e: React.FormEvent) {
		e.preventDefault();
		if (!canSubmit) return;
		setStatus("sending");
		setErrMsg(null);
		const r = await postJson("/api/compose", {
			agentId: target,
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

	return (
		<form
			onSubmit={handleSend}
			className="border-t border-(--color-border-soft) bg-white px-6 py-3"
		>
			<div className="mb-1.5 flex items-center justify-between text-[10px] text-fg-dim">
				<span>
					Replying to <span className="text-fg-muted">{target}</span> on this thread
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
