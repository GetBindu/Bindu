import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router";
import clsx from "clsx";
import {
	TrayIcon,
	MagnifyingGlassIcon,
	XIcon,
	ShieldCheckIcon,
	ArrowsClockwiseIcon,
	CopyIcon,
	CheckIcon,
} from "@phosphor-icons/react";
import { useUI } from "~/state";
import { useAllEvents } from "~/lib/hooks";
import { ThreadList } from "./ThreadList";
import { ThreadView } from "./ThreadView";
import { DraftList } from "./DraftList";
import {
	extractContextId,
	groupByThread,
	shortContextId,
	threadInFolder,
} from "~/lib/threads";
import type { StreamEvent } from "~/types";

function DetailRailToggle() {
	const showDetailRail = useUI((s) => s.showDetailRail);
	const toggleDetailRail = useUI((s) => s.toggleDetailRail);
	return (
		<button
			type="button"
			onClick={toggleDetailRail}
			title={showDetailRail ? "Hide auditor panel" : "Show auditor panel"}
			className={clsx(
				"flex items-center gap-1.5 rounded-md border bg-white px-2 py-1 text-[11px] transition",
				showDetailRail
					? "border-(--color-cobalt) text-(--color-cobalt)"
					: "border-(--color-border) text-fg-muted hover:border-(--color-cobalt) hover:text-(--color-cobalt)",
			)}
		>
			<ShieldCheckIcon size={11} weight="bold" />
			Verify
		</button>
	);
}

/** Build a structured text dump of the current view, suitable for
 * pasting into a chat / issue. Two shapes:
 *
 *   - Thread open → full event log of that thread (most useful for
 *     "look at what this conversation did" share)
 *   - Folder view → one-line summary per thread, scoped to the
 *     current folder + search query
 *
 * Plain text, not JSON, so a human reading the paste can scan it
 * without needing a pretty-printer. */
function buildViewDump(opts: {
	events: StreamEvent[];
	folderLabel: string;
	folder: "inbox" | "sent" | "archive" | null;
	query: string;
	selectedThreadId: string | null;
	archivedThreads: Set<string>;
}): string {
	const { events, folderLabel, folder, query, selectedThreadId, archivedThreads } =
		opts;
	const lines: string[] = [];
	lines.push(`# Bindu Inbox · ${folderLabel}`);
	if (query) lines.push(`search: "${query}"`);
	lines.push("");

	if (selectedThreadId) {
		const threadEvents = events
			.filter((e) => extractContextId(e) === selectedThreadId)
			.sort((a, b) => (a.at ?? a.ts).localeCompare(b.at ?? b.ts));
		lines.push(`## thread ${shortContextId(selectedThreadId)}  (full id: ${selectedThreadId})`);
		lines.push(`${threadEvents.length} events`);
		lines.push("");
		for (const e of threadEvents) {
			const state = e.state ? ` ${e.state}` : "";
			const cp =
				e.counterparty?.did && e.counterparty.did !== "—"
					? ` ← ${e.counterparty.did}`
					: "";
			lines.push(
				`- [${e.agentId}] ${e.ts}${state}  ${e.summary}${cp}`.slice(0, 500),
			);
			// Inline the message body (outbound text + artifact answer)
			// on continuation lines so the paste actually carries content
			// instead of just "Artifact delivered". Cap each event's body
			// to keep large markdown answers from drowning the dump.
			if (e.body) {
				const truncated = e.body.length > 1200
					? e.body.slice(0, 1200) + "\n…[truncated]"
					: e.body;
				for (const ln of truncated.split("\n")) {
					lines.push(`    ${ln}`);
				}
			}
		}
		return lines.join("\n");
	}

	const grouped = groupByThread(events);
	const scoped = folder
		? grouped.filter((t) => threadInFolder(t, folder, archivedThreads))
		: grouped;
	const matches = query
		? scoped.filter((t) =>
				`${t.contextId} ${t.latest.summary} ${t.earliest.summary}`
					.toLowerCase()
					.includes(query.toLowerCase()),
			)
		: scoped;

	lines.push(`${matches.length} thread${matches.length === 1 ? "" : "s"}`);
	lines.push("");
	for (const t of matches) {
		const peer = t.otherPartyAgentId ?? "(unknown)";
		const peerDid =
			t.earliest.payloadJson?.to_did ??
			t.earliest.counterparty?.did ??
			"";
		const state = t.latest.state ?? "?";
		lines.push(`## ${shortContextId(t.contextId)}`);
		lines.push(`  origin: ${t.origin} ↔ ${peer}${peerDid ? `  (${peerDid})` : ""}`);
		lines.push(`  state:  ${state}`);
		lines.push(`  ${t.totalCount} events across ${t.agentIds.size} lane(s): ${[...t.agentIds].join(", ")}`);
		lines.push(`  preview: ${(t.latest.summary || "").slice(0, 200)}`);
		lines.push("");
	}
	return lines.join("\n").trimEnd();
}

function CopyViewButton({
	events,
	folderLabel,
	folder,
	query,
	selectedThreadId,
	archivedThreads,
}: {
	events: StreamEvent[];
	folderLabel: string;
	folder: "inbox" | "sent" | "archive" | null;
	query: string;
	selectedThreadId: string | null;
	archivedThreads: Set<string>;
}) {
	const [copied, setCopied] = useState(false);
	async function onClick() {
		const dump = buildViewDump({
			events,
			folderLabel,
			folder,
			query,
			selectedThreadId,
			archivedThreads,
		});
		try {
			await navigator.clipboard.writeText(dump);
			setCopied(true);
			setTimeout(() => setCopied(false), 1400);
		} catch {
			/* clipboard blocked — fail silent */
		}
	}
	return (
		<button
			type="button"
			onClick={onClick}
			title={
				selectedThreadId
					? "Copy this thread as text"
					: "Copy this folder's threads as text"
			}
			className="flex items-center gap-1 rounded-md border border-(--color-border) bg-white px-2 py-1 text-[11px] text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
		>
			{copied ? (
				<>
					<CheckIcon size={11} weight="bold" />
					Copied
				</>
			) : (
				<>
					<CopyIcon size={11} weight="bold" />
					Copy
				</>
			)}
		</button>
	);
}

function RefreshButton() {
	const hydrateThreadState = useUI((s) => s.hydrateThreadState);
	const [spinning, setSpinning] = useState(false);
	async function onClick() {
		setSpinning(true);
		try {
			await hydrateThreadState();
		} finally {
			// Keep the spin visible briefly so the click feels real.
			setTimeout(() => setSpinning(false), 350);
		}
	}
	return (
		<button
			type="button"
			onClick={onClick}
			title="Refresh"
			className="flex items-center rounded-md border border-(--color-border) bg-white p-1.5 text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
		>
			<ArrowsClockwiseIcon
				size={12}
				weight="bold"
				className={spinning ? "animate-spin" : undefined}
			/>
		</button>
	);
}

type Folder = "inbox" | "sent" | "drafts" | "archive";
type Mode = { kind: "folder"; folder: Folder } | { kind: "agent"; agentId: string };

function useMode(): Mode {
	const loc = useLocation();
	const params = useParams<{ agentId: string }>();
	if (loc.pathname === "/sent") return { kind: "folder", folder: "sent" };
	if (loc.pathname === "/archive") return { kind: "folder", folder: "archive" };
	if (loc.pathname === "/drafts") return { kind: "folder", folder: "drafts" };
	if (loc.pathname === "/inbox" || loc.pathname === "/")
		return { kind: "folder", folder: "inbox" };
	return { kind: "agent", agentId: params.agentId ?? "writer" };
}

export function StreamPanel() {
	const mode = useMode();
	const allEvents = useAllEvents();
	const selectedThreadId = useUI((s) => s.selectedThreadId);
	const selectThread = useUI((s) => s.selectThread);
	const archivedThreads = useUI((s) => s.archivedThreads);
	const [query, setQuery] = useState("");

	// Clear the open thread + search when the user switches folder / agent —
	// a context_id and a search term belong to one selection, not another's.
	const modeKey = mode.kind === "folder" ? `folder:${mode.folder}` : `agent:${mode.agentId}`;
	useEffect(() => {
		selectThread(null);
		setQuery("");
	}, [modeKey, selectThread]);

	// For folder modes we hand ALL events to ThreadList so threads can be
	// grouped across both lanes (outbox + recipient agent) and the sender
	// label can be derived from the originating event. The folder filter
	// is then applied at the THREAD level inside ThreadList. The agent
	// debug mode keeps the legacy per-lane filter.
	const filteredEvents = useMemo(() => {
		if (mode.kind === "agent") {
			return allEvents.filter((e) => e.agentId === mode.agentId);
		}
		return allEvents;
	}, [mode, allEvents]);

	const FOLDER_TITLES: Record<Folder, string> = {
		inbox: "Inbox",
		sent: "Sent",
		drafts: "Drafts",
		archive: "Archive",
	};
	const title =
		mode.kind === "folder" ? FOLDER_TITLES[mode.folder] : mode.agentId;

	return (
		<main className="flex min-w-0 flex-1 flex-col">
			<header className="flex items-center justify-between gap-4 border-b border-(--color-border-soft) bg-(--color-panel) px-6 py-3">
				<div className="flex min-w-0 items-center gap-2.5">
					{mode.kind === "folder" && (
						<TrayIcon size={18} weight="duotone" className="text-fg-muted" />
					)}
					<h1 className="shrink-0 text-[15px] font-semibold text-fg">{title}</h1>
				</div>
				<div className="relative max-w-[320px] flex-1">
					<MagnifyingGlassIcon
						size={12}
						weight="bold"
						className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-fg-dim"
					/>
					<input
						type="text"
						value={query}
						onChange={(e) => setQuery(e.target.value)}
						placeholder="Search in this folder…"
						className="w-full rounded-md border border-(--color-border-soft) bg-slate-50 py-1 pl-6 pr-7 text-[12px] text-fg placeholder-fg-faint outline-none transition focus:border-(--color-cobalt) focus:bg-white focus:ring-2 focus:ring-(--color-cobalt-soft)"
					/>
					{query && (
						<button
							type="button"
							onClick={() => setQuery("")}
							title="Clear"
							className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-0.5 text-fg-dim hover:bg-slate-200 hover:text-fg"
						>
							<XIcon size={10} weight="bold" />
						</button>
					)}
				</div>
				<div className="flex items-center gap-2">
					<CopyViewButton
						events={filteredEvents}
						folderLabel={title}
						folder={
							mode.kind === "folder" && mode.folder !== "drafts"
								? mode.folder
								: null
						}
						query={query}
						selectedThreadId={selectedThreadId}
						archivedThreads={archivedThreads}
					/>
					<RefreshButton />
					{selectedThreadId && <DetailRailToggle />}
				</div>
			</header>
			{/* MailboxSplitView — list shrinks to 380px when a thread opens,
			    the thread renders to the right. On mobile the list hides
			    when a thread is open (the view takes the full width).
			    Drafts is a list-only folder: clicking a draft opens the
			    compose modal instead of expanding a thread view. */}
			<div className="flex min-h-0 flex-1">
				<div
					className={clsx(
						"flex min-h-0 flex-col",
						selectedThreadId
							? "hidden md:flex md:w-[380px] md:shrink-0 md:border-r md:border-(--color-border-soft)"
							: "flex-1",
					)}
				>
					<div className="scrollbar flex-1 overflow-y-auto">
						{mode.kind === "folder" && mode.folder === "drafts" ? (
							<DraftList />
						) : (
							<ThreadList
								events={filteredEvents}
								mode={
									mode.kind === "folder" && mode.folder !== "drafts"
										? mode.folder
										: "inbox"
								}
								query={query}
							/>
						)}
					</div>
				</div>
				{selectedThreadId && (
					<div className="flex min-w-0 flex-1 flex-col overflow-hidden">
						<ThreadView contextId={selectedThreadId} />
					</div>
				)}
			</div>
		</main>
	);
}
