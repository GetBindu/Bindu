import clsx from "clsx";
import { WarningIcon } from "@phosphor-icons/react";
import { useUI } from "~/state";
import {
	groupByThread,
	shortContextId,
	type Thread,
} from "~/lib/threads";
import { kindGlyph, stateMeta } from "~/lib/format";
import type { StreamEvent } from "~/types";

interface Props {
	events: StreamEvent[];
}

export function ThreadList({ events }: Props) {
	const selectThread = useUI((s) => s.selectThread);
	const selectEvent = useUI((s) => s.selectEvent);
	const threads = groupByThread(events);

	if (threads.length === 0) {
		return (
			<div className="flex h-40 items-center justify-center text-[12px] text-fg-dim">
				No conversations yet for this agent.
			</div>
		);
	}

	const attention = threads.filter((t) => t.attentionCount > 0);
	const regular = threads.filter((t) => t.attentionCount === 0);

	function open(t: Thread) {
		selectThread(t.contextId);
		selectEvent(t.latest.id);
	}

	return (
		<>
			{attention.length > 0 && (
				<section className="border-b border-yellow-300/60 bg-yellow-50/60">
					<div className="flex items-center justify-between px-6 pb-2 pt-3">
						<div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-yellow-800">
							<WarningIcon size={12} weight="fill" />
							Needs Attention ({attention.length})
						</div>
						<span className="text-[10px] text-fg-dim">
							threads waiting for your input
						</span>
					</div>
					{attention.map((t) => (
						<ThreadRow key={t.contextId} thread={t} attentionLane onOpen={open} />
					))}
				</section>
			)}

			<div className="px-6 pb-2 pt-4 text-[10px] uppercase tracking-[0.15em] text-fg-dim">
				Inbox
			</div>
			{regular.map((t) => (
				<ThreadRow key={t.contextId} thread={t} attentionLane={false} onOpen={open} />
			))}
		</>
	);
}

function ThreadRow({
	thread,
	attentionLane,
	onOpen,
}: {
	thread: Thread;
	attentionLane: boolean;
	onOpen: (t: Thread) => void;
}) {
	const e = thread.latest;
	const sb = e.state ? stateMeta[e.state] : null;
	return (
		<button
			type="button"
			onClick={() => onOpen(thread)}
			className={clsx(
				"group flex w-full items-start gap-3 border-b border-[--color-border-soft] px-6 py-3 text-left transition hover:bg-[--color-row-hover]",
				attentionLane && "bg-yellow-50/40",
			)}
		>
			<span className="mt-0.5 w-4 shrink-0 text-center text-[14px] text-fg-dim">
				{kindGlyph[e.kind]}
			</span>

			<div className="min-w-0 flex-1">
				<div className="flex flex-wrap items-center gap-x-2 gap-y-1">
					<span className="text-[13px] text-fg">
						{e.counterparty.name === "task"
							? `Thread ${shortContextId(thread.contextId)}`
							: e.counterparty.name}
					</span>
					<span className="text-[10px] text-fg-dim">
						{shortContextId(thread.contextId)}
					</span>
					{sb && e.state && (
						<span
							className={clsx(
								"rounded border px-1 text-[9px] uppercase tracking-wide",
								sb.bg,
								sb.color,
								sb.border,
							)}
						>
							{e.state}
						</span>
					)}
					{thread.totalCount > 1 && (
						<span className="rounded-full bg-slate-100 px-1.5 text-[10px] text-slate-700">
							{thread.totalCount}
						</span>
					)}
				</div>
				<div className="mt-0.5 truncate text-[12px] text-fg-muted">{e.summary}</div>
			</div>

			<div className="flex shrink-0 flex-col items-end gap-1">
				<span className="text-[10px] text-fg-dim">{e.relTs}</span>
				{thread.attentionCount > 0 && (
					<span className="rounded-md bg-[--color-sunflower] px-2 py-0.5 text-[10px] font-medium text-yellow-900 group-hover:bg-[--color-sunflower-strong]">
						{thread.attentionCount} need{thread.attentionCount === 1 ? "s" : ""} you
					</span>
				)}
			</div>
		</button>
	);
}
