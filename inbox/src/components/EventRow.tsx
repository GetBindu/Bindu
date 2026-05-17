import { useState } from "react";
import clsx from "clsx";
import { InfoIcon, PaperPlaneTiltIcon } from "@phosphor-icons/react";
import { useUI } from "~/state";
import { kindGlyph, shortDid, stateMeta, trustMeta } from "~/lib/format";
import { postJson } from "~/lib/fetch";
import type { StreamEvent } from "~/types";

interface Props {
	event: StreamEvent;
	attentionLane: boolean;
}

export function EventRow({ event, attentionLane }: Props) {
	const selectedEventId = useUI((s) => s.selectedEventId);
	const selectEvent = useUI((s) => s.selectEvent);
	const [infoOpen, setInfoOpen] = useState(false);

	const isSelected = selectedEventId === event.id;
	const tb = trustMeta[event.counterparty.trust];
	const sb = event.state ? stateMeta[event.state] : null;

	return (
		<div
			className={clsx(
				"border-b border-(--color-border-soft) transition",
				isSelected
					? "bg-(--color-cobalt-soft)"
					: "hover:bg-(--color-row-hover)",
				attentionLane && !isSelected && "bg-yellow-50/40",
			)}
		>
			<button
				type="button"
				onClick={() => selectEvent(event.id)}
				className="group flex w-full items-start gap-3 px-6 py-2.5 text-left"
			>
				<span className="mt-0.5 w-4 shrink-0 text-center text-[14px] text-fg-dim">
					{kindGlyph[event.kind]}
				</span>

				<div className="min-w-0 flex-1">
					<div className="flex flex-wrap items-center gap-x-2 gap-y-1">
						<span className="text-[13px] text-fg">{event.counterparty.name}</span>
						<span className="text-[10px] text-fg-dim">
							{shortDid(event.counterparty.did)}
						</span>
						<span
							className={clsx(
								"rounded border px-1 text-[9px] uppercase tracking-wide",
								tb.bg,
								tb.color,
								tb.border,
							)}
						>
							{tb.label}
						</span>
						{sb && event.state && (
							<span
								className={clsx(
									"rounded border px-1 text-[9px] uppercase tracking-wide",
									sb.bg,
									sb.color,
									sb.border,
								)}
							>
								{event.state}
							</span>
						)}
						{event.signed && (
							<span className="text-[10px] text-(--color-cobalt)">✓</span>
						)}
						{event.body && (
							<span className="text-[10px] text-fg-dim">{event.summary}</span>
						)}
					</div>
					{event.body ? (
						<div className="mt-1 whitespace-pre-wrap text-[13px] text-fg">
							{event.body}
						</div>
					) : (
						<div className="mt-0.5 truncate text-[12px] text-fg-muted">
							{event.summary}
						</div>
					)}
				</div>

				<div className="flex shrink-0 flex-col items-end gap-1">
					<div className="flex items-center gap-1.5">
						<span className="text-[10px] text-fg-dim">{event.relTs}</span>
						<span
							role="button"
							tabIndex={0}
							title={infoOpen ? "Hide IDs" : "Show task / context / event IDs"}
							onClick={(e) => {
								e.stopPropagation();
								setInfoOpen((o) => !o);
							}}
							onKeyDown={(e) => {
								if (e.key === "Enter" || e.key === " ") {
									e.preventDefault();
									e.stopPropagation();
									setInfoOpen((o) => !o);
								}
							}}
							className={clsx(
								"flex h-4 w-4 cursor-pointer items-center justify-center rounded-sm transition",
								infoOpen
									? "text-(--color-cobalt)"
									: "text-fg-dim hover:text-(--color-cobalt)",
							)}
						>
							<InfoIcon size={11} weight={infoOpen ? "fill" : "regular"} />
						</span>
					</div>
					{event.action && (
						<span className="rounded-md bg-(--color-sunflower) px-2 py-0.5 text-[10px] font-medium text-yellow-900 group-hover:bg-(--color-sunflower-strong)">
							{event.action.label}
						</span>
					)}
				</div>
			</button>

			{infoOpen && <IdStrip event={event} />}

			{event.action && (
				<InlineActionForm
					eventId={event.id}
					actionKind={event.action.kind}
					actionLabel={event.action.label}
				/>
			)}
		</div>
	);
}

/**
 * Toggle-revealed strip of correlation IDs for the row. Surfaces the
 * pieces operators reach for first when debugging: the event_id (for
 * log grep), task_id (per-task A2A lifecycle), context_id (Gmail-style
 * thread key), reference_task_ids (when a turn replies to a prior
 * task) and message_id (for outbound rows). Pulled out of the row
 * button so clicking IDs to text-select / copy doesn't also trigger
 * row selection.
 */
function IdStrip({ event }: { event: StreamEvent }) {
	const p = event.payloadJson ?? {};
	const taskId = typeof p.task_id === "string" ? p.task_id : undefined;
	const contextId = typeof p.context_id === "string" ? p.context_id : undefined;
	const messageId = typeof p.message_id === "string" ? p.message_id : undefined;
	const refIds = Array.isArray(p.reference_task_ids)
		? (p.reference_task_ids as unknown[]).filter(
				(v): v is string => typeof v === "string",
			)
		: [];
	const parentId = typeof p.parent_id === "string" ? p.parent_id : undefined;

	return (
		<div className="px-6 pb-2 pl-[3.25rem]">
			<dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-0.5 text-[11px]">
				<IdRow label="event" value={event.id} />
				{taskId && <IdRow label="task" value={taskId} />}
				{contextId && <IdRow label="context" value={contextId} />}
				{messageId && <IdRow label="message" value={messageId} />}
				{parentId && <IdRow label="parent" value={parentId} />}
				{refIds.length > 0 && <IdRow label="refs" value={refIds.join(", ")} />}
			</dl>
		</div>
	);
}

function IdRow({ label, value }: { label: string; value: string }) {
	return (
		<>
			<dt className="text-fg-dim uppercase tracking-wide text-[9px] self-center">
				{label}
			</dt>
			<dd className="font-mono text-fg-muted break-all select-all">{value}</dd>
		</>
	);
}

/**
 * Inline action form rendered directly below an action-required row.
 * Mirrors the side-rail ActionPanel but lives where the user's eye
 * already is — Gmail-shape reply, not a hidden auditor panel.
 *
 * For `input` actions: textarea + primary button + decline. Other
 * action kinds (`approve`, `pay`) skip the textarea and just expose
 * the two buttons. Status (`delivered` / `recorded` / `error`) lands
 * underneath so the user knows the call went through; the row stays
 * present until the agent emits the next state event.
 */
function InlineActionForm({
	eventId,
	actionKind,
	actionLabel,
}: {
	eventId: string;
	actionKind: "approve" | "input" | "pay";
	actionLabel: string;
}) {
	const [text, setText] = useState("");
	const [status, setStatus] = useState<
		"idle" | "sending" | "delivered" | "recorded" | "error"
	>("idle");
	const [errMsg, setErrMsg] = useState<string | null>(null);

	const isInput = actionKind === "input";
	const isDone = status === "delivered" || status === "recorded";
	const canSubmit =
		status !== "sending" && !isDone && (!isInput || text.trim().length > 0);

	async function send(
		kind: "approve" | "decline" | "input" | "pay",
		body?: { text?: string },
	) {
		setStatus("sending");
		setErrMsg(null);
		const r = await postJson<{ delivered?: boolean; protocolMovePending?: boolean }>(
			`/api/events/${encodeURIComponent(eventId)}/action`,
			{ kind, ...body },
		);
		if (!r.ok) {
			setStatus("error");
			setErrMsg(r.errMsg);
			return;
		}
		if (r.data?.protocolMovePending) {
			setStatus("recorded");
		} else {
			setStatus("delivered");
		}
		setText("");
	}

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault();
		if (!canSubmit) return;
		await send(actionKind, isInput ? { text } : undefined);
	}

	return (
		<form
			onSubmit={handleSubmit}
			className="px-6 pb-3 pl-[3.25rem]"
		>
			{isInput && (
				<textarea
					value={text}
					onChange={(e) => setText(e.target.value)}
					onKeyDown={(e) => {
						if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
							handleSubmit(e as unknown as React.FormEvent);
						}
					}}
					placeholder="Type your response… (⌘↩ to send)"
					rows={2}
					disabled={isDone || status === "sending"}
					className="w-full resize-none rounded-md border border-(--color-border) bg-white px-3 py-2 text-[13px] text-fg placeholder-fg-faint outline-none transition focus:border-(--color-cobalt) focus:ring-2 focus:ring-(--color-cobalt-soft) disabled:bg-slate-50 disabled:text-fg-dim"
				/>
			)}
			<div className={clsx("flex items-center gap-2", isInput && "mt-2")}>
				<button
					type="button"
					disabled={status === "sending" || isDone}
					onClick={() => send("decline")}
					className="rounded-md border border-(--color-border) bg-white px-3 py-1.5 text-[12px] text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt) disabled:opacity-50"
				>
					Decline
				</button>
				{status === "delivered" && (
					<span className="text-[10px] text-(--color-cobalt)">
						✓ delivered to agent
					</span>
				)}
				{status === "recorded" && (
					<span className="text-[10px] text-fg-muted">
						✓ recorded — protocol callback not wired yet
					</span>
				)}
				{status === "error" && errMsg && (
					<span className="text-[10px] text-rose-700">✗ {errMsg}</span>
				)}
				<button
					type="submit"
					disabled={!canSubmit}
					className={clsx(
						"ml-auto flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[12px] font-medium shadow-sm transition",
						canSubmit
							? "bg-(--color-cobalt) text-white hover:bg-(--color-cobalt-strong)"
							: "bg-slate-200 text-slate-400",
					)}
				>
					<PaperPlaneTiltIcon size={12} weight="fill" />
					{status === "sending" ? "Sending…" : actionLabel}
				</button>
			</div>
		</form>
	);
}
