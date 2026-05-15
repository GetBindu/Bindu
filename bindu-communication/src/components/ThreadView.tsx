import { ArrowLeftIcon } from "@phosphor-icons/react";
import { useUI } from "~/state";
import { eventsInThread, shortContextId } from "~/lib/threads";
import { EventRow } from "./EventRow";
import type { StreamEvent } from "~/types";

interface Props {
	contextId: string;
	events: StreamEvent[];
}

/**
 * One thread's events, oldest → newest. Reuses EventRow for each entry —
 * gateway parent/child trace indenting still works because EventRow looks
 * at its `indented` prop. We don't pass it here (threads are flat); the
 * trace concept lives inside the chronological event log, not the
 * Gmail-shape thread view.
 */
export function ThreadView({ contextId, events }: Props) {
	const selectThread = useUI((s) => s.selectThread);
	const ordered = eventsInThread(events, contextId);
	const first = ordered[0];
	const counterpartyName = first?.counterparty.name ?? "—";

	return (
		<>
			<div className="flex items-center gap-2 border-b border-[--color-border-soft] bg-white px-6 py-2.5">
				<button
					type="button"
					onClick={() => selectThread(null)}
					className="flex items-center gap-1 rounded-md border border-[--color-border-soft] bg-white px-2 py-1 text-[11px] text-fg-muted transition hover:border-[--color-cobalt] hover:text-[--color-cobalt]"
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
				<span className="text-[10px] text-fg-dim">
					{ordered.length} message{ordered.length === 1 ? "" : "s"}
				</span>
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
							hasChildren={false}
							indented={false}
							attentionLane={!!e.needsAttention}
						/>
					))
				)}
			</div>
		</>
	);
}
