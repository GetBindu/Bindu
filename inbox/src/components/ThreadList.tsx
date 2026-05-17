import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import {
	ArchiveIcon,
	ArrowArcLeftIcon,
	ArrowBendUpLeftIcon,
	CheckIcon,
	EnvelopeOpenIcon,
	EnvelopeSimpleIcon,
	TrayIcon,
	XIcon,
} from "@phosphor-icons/react";
import { useUI } from "~/state";
import {
	groupByThread,
	shortContextId,
	threadInFolder,
	type Thread,
} from "~/lib/threads";
import { formatListDate } from "~/lib/format";
import type { StreamEvent } from "~/types";

interface Props {
	events: StreamEvent[];
	mode?: "inbox" | "sent" | "archive";
	query?: string;
}

function matchesQuery(t: Thread, q: string): boolean {
	if (!q) return true;
	const needle = q.toLowerCase();
	const e = t.latest;
	if (e.counterparty.name.toLowerCase().includes(needle)) return true;
	if (e.counterparty.did.toLowerCase().includes(needle)) return true;
	if (e.summary.toLowerCase().includes(needle)) return true;
	if (t.contextId.toLowerCase().includes(needle)) return true;
	const p = e.payloadJson;
	if (p) {
		if (typeof p.text === "string" && p.text.toLowerCase().includes(needle)) return true;
		if (typeof p.event_type === "string" && p.event_type.toLowerCase().includes(needle)) return true;
	}
	return false;
}

/**
 * Gmail-shape thread list. Each row mirrors the agentic-inbox layout:
 *
 *   • dot · sender · count · needs-reply · date          [hover: mark read/unread]
 *                                          subject — snippet
 *
 * "Unread" is computed from explicit overrides first, then falls back to
 * attentionCount > 0. Overrides persist to localStorage so the user's
 * triage state survives refreshes.
 */
export function ThreadList({ events, mode = "inbox", query = "" }: Props) {
	const selectThread = useUI((s) => s.selectThread);
	const selectEvent = useUI((s) => s.selectEvent);
	const readOverrides = useUI((s) => s.readOverrides);
	const unreadOverrides = useUI((s) => s.unreadOverrides);
	const markRead = useUI((s) => s.markRead);
	const markUnread = useUI((s) => s.markUnread);
	const archiveThread = useUI((s) => s.archiveThread);
	const unarchiveThread = useUI((s) => s.unarchiveThread);
	const archivedThreads = useUI((s) => s.archivedThreads);
	// `groupByThread` walks the entire event buffer twice — pulling it
	// inside useMemo means we only rebuild when the buffer itself changes,
	// not on every selection/keystroke. Folder + query filtering is cheap
	// (per-thread predicates), so they stay outside.
	const grouped = useMemo(() => groupByThread(events), [events]);
	const folderScoped = useMemo(
		() =>
			mode === "inbox" || mode === "sent" || mode === "archive"
				? grouped.filter((t) => threadInFolder(t, mode, archivedThreads))
				: grouped,
		[grouped, mode, archivedThreads],
	);
	const threads = useMemo(
		() =>
			query
				? folderScoped.filter((t) => matchesQuery(t, query))
				: folderScoped,
		[folderScoped, query],
	);

	// Bulk selection — local to this list. Cleared when folder/query/mode
	// changes (folder switch already remounts via key but the query change
	// doesn't, so reset explicitly).
	const [selected, setSelected] = useState<Set<string>>(new Set());
	useEffect(() => {
		setSelected(new Set());
	}, [mode, query]);

	function toggleSelected(contextId: string) {
		setSelected((prev) => {
			const next = new Set(prev);
			if (next.has(contextId)) next.delete(contextId);
			else next.add(contextId);
			return next;
		});
	}
	function clearSelected() {
		setSelected(new Set());
	}
	function selectAllVisible() {
		setSelected(new Set(threads.map((t) => t.contextId)));
	}

	function isUnread(t: Thread): boolean {
		if (unreadOverrides.has(t.contextId)) return true;
		if (readOverrides.has(t.contextId)) return false;
		return t.attentionCount > 0;
	}

	function bulk(action: "read" | "unread" | "archive" | "unarchive") {
		for (const ctx of selected) {
			if (action === "read") markRead(ctx);
			else if (action === "unread") markUnread(ctx);
			else if (action === "archive") archiveThread(ctx);
			else if (action === "unarchive") unarchiveThread(ctx);
		}
		clearSelected();
	}

	if (threads.length === 0) {
		const isFiltered = !!query && folderScoped.length > 0;
		return (
			<div className="flex flex-col items-center justify-center px-6 py-24 text-center">
				<TrayIcon size={48} weight="thin" className="mb-4 text-fg-dim" />
				<h3 className="mb-1 text-[15px] font-semibold text-fg">
					{isFiltered ? "No matches" : "Nothing to show"}
				</h3>
				<p className="max-w-xs text-[12px] text-fg-muted">
					{isFiltered
						? `No threads matched “${query}”. Clear the search to see all threads.`
						: "When a thread arrives in this folder, it'll appear here."}
				</p>
			</div>
		);
	}

	function open(t: Thread) {
		selectThread(t.contextId);
		selectEvent(t.latest.id);
	}

	return (
		<div>
			{selected.size > 0 && (
				<div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-(--color-border) bg-(--color-cobalt-soft) px-6 py-2 text-[12px]">
					<div className="flex items-center gap-2">
						<button
							type="button"
							onClick={clearSelected}
							title="Clear selection"
							className="rounded p-1 text-fg-muted hover:bg-white hover:text-fg"
						>
							<XIcon size={12} weight="bold" />
						</button>
						<span className="font-medium text-(--color-cobalt-strong)">
							{selected.size} selected
						</span>
						<button
							type="button"
							onClick={selectAllVisible}
							className="text-[11px] text-fg-muted underline-offset-2 hover:text-fg hover:underline"
						>
							Select all {threads.length}
						</button>
					</div>
					<div className="flex items-center gap-1">
						<button
							type="button"
							onClick={() => bulk("read")}
							title="Mark selected as read"
							className="flex items-center gap-1 rounded-md border border-(--color-border) bg-white px-2 py-1 text-[11px] text-fg-muted hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
						>
							<EnvelopeOpenIcon size={11} weight="bold" />
							Read
						</button>
						<button
							type="button"
							onClick={() => bulk("unread")}
							title="Mark selected as unread"
							className="flex items-center gap-1 rounded-md border border-(--color-border) bg-white px-2 py-1 text-[11px] text-fg-muted hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
						>
							<EnvelopeSimpleIcon size={11} weight="bold" />
							Unread
						</button>
						{mode === "archive" ? (
							<button
								type="button"
								onClick={() => bulk("unarchive")}
								title="Restore selected"
								className="flex items-center gap-1 rounded-md border border-(--color-border) bg-white px-2 py-1 text-[11px] text-fg-muted hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
							>
								<ArrowArcLeftIcon size={11} weight="bold" />
								Restore
							</button>
						) : (
							<button
								type="button"
								onClick={() => bulk("archive")}
								title="Archive selected"
								className="flex items-center gap-1 rounded-md border border-(--color-border) bg-white px-2 py-1 text-[11px] text-fg-muted hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
							>
								<ArchiveIcon size={11} weight="bold" />
								Archive
							</button>
						)}
					</div>
				</div>
			)}
			{threads.map((t) => (
				<ThreadRow
					key={t.contextId}
					thread={t}
					unread={isUnread(t)}
					mode={mode}
					selected={selected.has(t.contextId)}
					onToggleSelect={() => toggleSelected(t.contextId)}
					onOpen={open}
					onMarkRead={() => markRead(t.contextId)}
					onMarkUnread={() => markUnread(t.contextId)}
					onArchive={() => archiveThread(t.contextId)}
					onUnarchive={() => unarchiveThread(t.contextId)}
				/>
			))}
		</div>
	);
}

function ThreadRow({
	thread,
	unread,
	mode,
	selected,
	onToggleSelect,
	onOpen,
	onMarkRead,
	onMarkUnread,
	onArchive,
	onUnarchive,
}: {
	thread: Thread;
	unread: boolean;
	mode: "inbox" | "sent" | "archive";
	selected: boolean;
	onToggleSelect: () => void;
	onOpen: (t: Thread) => void;
	onMarkRead: () => void;
	onMarkUnread: () => void;
	onArchive: () => void;
	onUnarchive: () => void;
}) {
	const e = thread.latest;
	const isUnread = unread;

	// Sender label is thread-origin-driven, not latest-event-driven, so an
	// inbound lifecycle row doesn't render as "Thread <ctx>" just because
	// the recipient agent's webhook didn't carry a name.
	const otherParty =
		thread.otherPartyAgentId ?? (e.counterparty.name !== "task" ? e.counterparty.name : null);
	const labelTarget = otherParty ?? shortContextId(thread.contextId);
	const fromLabel = thread.origin === "operator" ? `To: ${labelTarget}` : labelTarget;

	// Subject = first message's text if we know it (outbound has text on
	// the payload), otherwise the latest summary. Snippet = latest summary.
	const subject = subjectFor(thread);
	const snippet = e.summary;

	return (
		<div
			role="button"
			tabIndex={0}
			onClick={() => onOpen(thread)}
			onKeyDown={(ev) => {
				if (ev.key === "Enter" || ev.key === " ") {
					ev.preventDefault();
					onOpen(thread);
				}
			}}
			className={clsx(
				"group flex w-full cursor-pointer items-center gap-3 border-b border-(--color-border-soft) px-4 py-3 text-left transition hover:bg-(--color-row-hover) md:px-6 md:py-3.5",
				isUnread && "bg-yellow-50/40",
				selected && "bg-(--color-cobalt-soft)",
			)}
		>
			{/* Selection checkbox — visible on hover or when selected. */}
			<button
				type="button"
				onClick={(ev) => {
					ev.stopPropagation();
					onToggleSelect();
				}}
				title={selected ? "Deselect" : "Select"}
				className={clsx(
					"flex h-4 w-4 shrink-0 items-center justify-center rounded border transition",
					selected
						? "border-(--color-cobalt) bg-(--color-cobalt) text-white"
						: "border-(--color-border) bg-white opacity-0 group-hover:opacity-100",
				)}
			>
				{selected && <CheckIcon size={9} weight="bold" />}
			</button>

			{/* Avatar — colored circle with first letter. Gmail-shape. */}
			<div className="relative shrink-0">
				<Avatar seed={labelTarget} />
				{isUnread && !selected && (
					<span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-(--color-cobalt) ring-2 ring-white" />
				)}
			</div>

			{/* Content */}
			<div className="min-w-0 flex-1">
				<div className="flex items-center gap-2">
					<span
						className={clsx(
							"truncate text-[13px]",
							isUnread
								? "font-semibold text-fg"
								: "text-fg-muted",
						)}
					>
						{fromLabel}
					</span>
					{thread.totalCount > 1 && (
						<span className="shrink-0 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-700">
							{thread.totalCount}
						</span>
					)}
					{isUnread && (
						<span
							className="shrink-0 text-(--color-sunflower-strong)"
							title="Needs your reply"
						>
							<ArrowBendUpLeftIcon size={12} weight="bold" />
						</span>
					)}
					<span className="ml-auto shrink-0 text-[11px] text-fg-dim">
						{formatListDate(e.at, e.relTs)}
					</span>
					{/* Hover actions — read/unread + archive/restore */}
					<div className="flex shrink-0 items-center gap-0.5 opacity-0 transition group-hover:opacity-100">
						<button
							type="button"
							onClick={(ev) => {
								ev.stopPropagation();
								if (isUnread) onMarkRead();
								else onMarkUnread();
							}}
							title={isUnread ? "Mark as read" : "Mark as unread"}
							className="rounded p-1 text-fg-dim hover:bg-slate-100 hover:text-(--color-cobalt)"
						>
							{isUnread ? (
								<EnvelopeOpenIcon size={13} weight="bold" />
							) : (
								<EnvelopeSimpleIcon size={13} weight="bold" />
							)}
						</button>
						{mode === "archive" ? (
							<button
								type="button"
								onClick={(ev) => {
									ev.stopPropagation();
									onUnarchive();
								}}
								title="Restore to inbox"
								className="rounded p-1 text-fg-dim hover:bg-slate-100 hover:text-(--color-cobalt)"
							>
								<ArrowArcLeftIcon size={13} weight="bold" />
							</button>
						) : (
							<button
								type="button"
								onClick={(ev) => {
									ev.stopPropagation();
									onArchive();
								}}
								title="Archive"
								className="rounded p-1 text-fg-dim hover:bg-slate-100 hover:text-(--color-cobalt)"
							>
								<ArchiveIcon size={13} weight="bold" />
							</button>
						)}
					</div>
				</div>
				<div className="mt-0.5 truncate text-[12px]">
					<span
						className={clsx(
							isUnread ? "font-medium text-fg" : "text-fg-muted",
						)}
					>
						{subject}
					</span>
					{snippet && snippet !== subject && (
						<span className="text-fg-dim"> — {snippet}</span>
					)}
				</div>
			</div>
		</div>
	);
}

/**
 * Best-effort "subject line" for a thread.
 *
 * Priority:
 *   1. Operator-canonical: an outbound event in this thread has the body
 *      text — that IS the subject in Gmail terms.
 *   2. Inbound state events get a humanized phrase (no "state → working").
 *   3. Otherwise fall back to a thread short id.
 */
function subjectFor(thread: Thread): string {
	// Try to read the outbound body from the EARLIEST outbound event in the
	// thread — operator-canonical "subject" of the conversation.
	if (thread.earliest.agentId === "outbox") {
		const text = thread.earliest.payloadJson?.text;
		if (typeof text === "string" && text.trim().length > 0) return text;
	}

	const e = thread.latest;

	// Outbound: latest event has the body text.
	const latestText = e.payloadJson?.text;
	if (typeof latestText === "string") return latestText;

	// Inbound + lifecycle: humanize the state instead of "state → working".
	if (e.state) {
		const map: Record<string, string> = {
			submitted: "New request received",
			pending: "Pending",
			working: "Working on it…",
			"input-required": "Needs your input",
			"payment-required": "Payment required",
			"auth-required": "Auth required",
			completed: "Completed",
			failed: "Failed",
		};
		if (map[e.state]) return map[e.state];
	}

	if (e.kind === "artifact") return "Artifact delivered";
	if (e.counterparty.name === "task") {
		return `Thread ${shortContextId(thread.contextId)}`;
	}
	return e.summary;
}

/**
 * Colored letter avatar, Gmail-shape. Hue is deterministic on the seed so
 * the same agent gets the same color across views and refreshes.
 */
function Avatar({ seed }: { seed: string }) {
	let h = 0;
	for (let i = 0; i < seed.length; i++) {
		h = (h * 31 + seed.charCodeAt(i)) | 0;
	}
	const hue = Math.abs(h) % 360;
	const initial = (seed.replace(/^did:bindu:[^:]+:/, "").trim()[0] ?? "?").toUpperCase();
	return (
		<div
			className="flex h-8 w-8 items-center justify-center rounded-full text-[12px] font-semibold text-white"
			style={{ backgroundColor: `hsl(${hue} 45% 50%)` }}
			aria-hidden
		>
			{initial}
		</div>
	);
}
