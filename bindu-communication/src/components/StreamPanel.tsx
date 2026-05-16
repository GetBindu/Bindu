import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router";
import clsx from "clsx";
import {
	PencilSimpleIcon,
	TrayIcon,
	MagnifyingGlassIcon,
	XIcon,
	ShieldCheckIcon,
} from "@phosphor-icons/react";
import { events as mockEvents } from "~/data/mock";
import { useUI } from "~/state";
import { ThreadList } from "./ThreadList";
import { ThreadView } from "./ThreadView";
import { DraftList } from "./DraftList";

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
					? "border-[--color-cobalt] text-[--color-cobalt]"
					: "border-[--color-border] text-fg-muted hover:border-[--color-cobalt] hover:text-[--color-cobalt]",
			)}
		>
			<ShieldCheckIcon size={11} weight="bold" />
			Verify
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
	const agents = useUI((s) => s.agents);
	const liveEvents = useUI((s) => s.liveEvents);
	const selectedThreadId = useUI((s) => s.selectedThreadId);
	const selectThread = useUI((s) => s.selectThread);
	const openCompose = useUI((s) => s.openCompose);
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
		const all = [...liveEvents, ...mockEvents];
		if (mode.kind === "agent") {
			return all.filter((e) => e.agentId === mode.agentId);
		}
		return all;
	}, [mode, liveEvents]);

	const FOLDER_TITLES: Record<Folder, string> = {
		inbox: "Inbox",
		sent: "Sent",
		drafts: "Drafts",
		archive: "Archive",
	};
	const title =
		mode.kind === "folder"
			? FOLDER_TITLES[mode.folder]
			: agents.find((a) => a.id === mode.agentId)?.name ?? mode.agentId;

	return (
		<main className="flex min-w-0 flex-1 flex-col">
			<header className="flex items-center justify-between gap-4 border-b border-[--color-border-soft] bg-[--color-panel] px-6 py-3">
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
						className="w-full rounded-md border border-[--color-border-soft] bg-slate-50 py-1 pl-6 pr-7 text-[12px] text-fg placeholder-fg-faint outline-none transition focus:border-[--color-cobalt] focus:bg-white focus:ring-2 focus:ring-[--color-cobalt-soft]"
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
					{selectedThreadId && <DetailRailToggle />}
					<button
						type="button"
						onClick={openCompose}
						className="flex items-center gap-1.5 rounded-md bg-[--color-cobalt] px-2.5 py-1 text-[11px] font-medium text-white shadow-sm transition hover:bg-[--color-cobalt-strong]"
					>
						<PencilSimpleIcon size={11} weight="fill" />
						Compose
					</button>
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
							? "hidden md:flex md:w-[380px] md:shrink-0 md:border-r md:border-[--color-border-soft]"
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
