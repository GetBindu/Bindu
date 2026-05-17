import { useEffect, useRef, useState } from "react";
import { NavLink } from "react-router";
import {
	PlusIcon,
	GlobeIcon,
	TrayIcon,
	PaperPlaneTiltIcon,
	PencilSimpleIcon,
	ArchiveIcon,
	FileIcon,
	TrashIcon,
	InfoIcon,
	DotsThreeIcon,
	PlayIcon,
	StopIcon,
	WarningIcon,
	GearIcon,
	IdentificationCardIcon,
} from "@phosphor-icons/react";
import { useUI } from "~/state";
import { shortDid } from "~/lib/format";
import { isGateway } from "~/lib/agent-kind";
import { AddAgentModal } from "./AddAgentModal";
import { AgentInfoModal } from "./AgentInfoModal";
import { SettingsModal } from "./SettingsModal";
import { postJson } from "~/lib/fetch";
import type { EcosystemAgent, PersonalAgent } from "~/lib/api-types";
import clsx from "clsx";

function useEcosystem() {
	const [list, setList] = useState<EcosystemAgent[]>([]);
	const [tick, setTick] = useState(0);
	useEffect(() => {
		let cancelled = false;
		const refresh = () => {
			// Skip when the tab isn't visible — no point hammering
			// /api/ecosystem every 5s in a background tab. The
			// visibilitychange listener below kicks an immediate refresh
			// the moment the user comes back.
			if (typeof document !== "undefined" && document.hidden) return;
			fetch("/api/ecosystem")
				.then((r) => (r.ok ? r.json() : []))
				.then((j) => {
					if (!cancelled) setList(j as EcosystemAgent[]);
				})
				.catch(() => {});
		};
		refresh();
		const t = setInterval(refresh, 5000);
		const onVis = () => {
			if (!document.hidden) refresh();
		};
		document.addEventListener("visibilitychange", onVis);
		return () => {
			cancelled = true;
			clearInterval(t);
			document.removeEventListener("visibilitychange", onVis);
		};
	}, [tick]);
	return { list, reload: () => setTick((n) => n + 1) };
}

const FOLDERS = [
	{ to: "/inbox", label: "Inbox", icon: TrayIcon },
	{ to: "/sent", label: "Sent", icon: PaperPlaneTiltIcon },
	{ to: "/drafts", label: "Drafts", icon: FileIcon },
	{ to: "/archive", label: "Archive", icon: ArchiveIcon },
] as const;

/**
 * Some agno-based agents don't publish /.well-known/did.json but DO embed
 * their DID inside agent_card.capabilities.extensions[].uri. Pull it from
 * there so the Contacts row shows the real DID instead of a "?" placeholder.
 */
function pickDidFromCard(
	card: { capabilities?: { extensions?: Array<{ uri?: string }> } | unknown } | null | undefined,
): string | null {
	const caps = (card?.capabilities ?? {}) as {
		extensions?: Array<{ uri?: string }>;
	};
	const exts = Array.isArray(caps.extensions) ? caps.extensions : [];
	for (const x of exts) {
		if (typeof x?.uri === "string" && x.uri.startsWith("did:")) return x.uri;
	}
	return null;
}

export function Sidebar() {
	const openCompose = useUI((s) => s.openCompose);
	const drafts = useUI((s) => s.drafts);
	const [showAdd, setShowAdd] = useState(false);
	const [showSettings, setShowSettings] = useState(false);
	const [infoFor, setInfoFor] = useState<EcosystemAgent | null>(null);
	const { list: ecosystem, reload: reloadEcosystem } = useEcosystem();

	return (
		<aside className="flex w-[256px] shrink-0 flex-col border-r border-(--color-border-soft) bg-(--color-sidebar)">
			{/* Brand */}
			<div className="flex items-center gap-2.5 border-b border-(--color-border-soft) px-4 py-4">
				<img
					src="/bindu.png"
					alt="Bindu"
					className="h-8 w-8 shrink-0 select-none"
					draggable={false}
				/>
				<div className="flex-1">
					<div className="text-[10px] uppercase tracking-[0.2em] text-fg-dim">
						Bindu
					</div>
					<div className="text-[14px] font-medium text-fg">Inbox</div>
				</div>
				{/* Settings — single gear icon in the brand bar. Gmail puts
				    this in the same spot. Opens a modal so we don't have to
				    add a route or shift the layout. */}
				<button
					type="button"
					onClick={() => setShowSettings(true)}
					title="Settings — API keys, Pipedream credentials"
					className="rounded-md p-1.5 text-fg-dim transition hover:bg-slate-100 hover:text-fg"
				>
					<GearIcon size={16} weight="duotone" />
				</button>
			</div>

			{/* Compose — hero action, Gmail-shape */}
			<div className="px-3 pt-4">
				<button
					type="button"
					onClick={openCompose}
					className="group flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-700 px-4 py-3 text-left text-[14px] font-semibold text-white shadow-md transition hover:bg-blue-800 hover:shadow-lg"
				>
					<PencilSimpleIcon size={18} weight="bold" />
					<span>Compose</span>
				</button>
			</div>

			{/* Folders */}
			<nav className="px-3 pt-3">
				{FOLDERS.map((f) => (
					<NavLink
						key={f.to}
						to={f.to}
						className={({ isActive }) =>
							clsx(
								"flex w-full items-center gap-3 rounded-md px-3 py-2 text-[13px] transition",
								isActive
									? "bg-(--color-cobalt-soft) font-medium text-fg"
									: "text-fg-muted hover:bg-(--color-row-hover)",
							)
						}
					>
						<f.icon size={16} weight="duotone" />
						<span className="flex-1">{f.label}</span>
						{f.to === "/drafts" && drafts.length > 0 && (
							<span className="rounded-full bg-slate-200 px-1.5 text-[10px] text-slate-700">
								{drafts.length}
							</span>
						)}
					</NavLink>
				))}
			</nav>

			{/* Ecosystem — split into Gateways (orchestrators that route
			    multi-agent plans) and Agents (single-purpose A2A peers).
			    The two roles look the same on the A2A wire but mean very
			    different things to the operator, so we surface the split
			    in the sidebar. flex-1 + min-h-0 lets the combined list
			    scroll when overflow happens; section headers stay
			    inline so the scroll bar covers both. */}
			<div className="mt-5 flex min-h-0 flex-1 flex-col px-3">
				<div className="flex shrink-0 items-center justify-between px-3 pb-1.5">
					<div className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-fg-dim">
						<GlobeIcon size={11} weight="bold" />
						Contacts
					</div>
					<button
						type="button"
						onClick={() => setShowAdd(true)}
						title="Add agent or gateway by URL"
						className="rounded p-0.5 text-fg-dim transition hover:bg-slate-100 hover:text-(--color-cobalt)"
					>
						<PlusIcon size={12} weight="bold" />
					</button>
				</div>
				<div className="scrollbar min-h-0 flex-1 overflow-y-auto">
					{(() => {
						// Hide the synthetic outbox bucket; it's the operator's
						// "Sent" folder, not a contact you'd ever write to.
						const visible = ecosystem.filter((a) => a.id !== "outbox");
						if (visible.length === 0) {
							return (
								<div className="px-3 py-1 text-[10px] text-fg-dim">
									No contacts. Click + to add.
								</div>
							);
						}
						const gateways = visible.filter(isGateway);
						const peers = visible.filter((a) => !isGateway(a));
						return (
							<>
								{gateways.length > 0 && (
									<ContactGroup
										title="Gateways"
										count={gateways.length}
										hint="Orchestrators — route multi-agent plans."
									>
										{gateways.map((a) => (
											<ContactRow
												key={a.id}
												agent={a}
												kind="gateway"
												onInfo={setInfoFor}
												onDelete={async () => {
													const name = a.agentCard?.name ?? a.id;
													if (!window.confirm(`Remove ${name} from contacts?`))
														return;
													await fetch(
														`/api/ecosystem/${encodeURIComponent(a.id)}`,
														{ method: "DELETE" },
													).catch(() => {});
													reloadEcosystem();
												}}
											/>
										))}
									</ContactGroup>
								)}
								{peers.length > 0 && (
									<ContactGroup
										title="Agents"
										count={peers.length}
										hint="Single-purpose A2A peers — pick one to message, two or more for a plan."
									>
										{peers.map((a) => (
											<ContactRow
												key={a.id}
												agent={a}
												kind="agent"
												onInfo={setInfoFor}
												onDelete={async () => {
													const name = a.agentCard?.name ?? a.id;
													if (!window.confirm(`Remove ${name} from contacts?`))
														return;
													await fetch(
														`/api/ecosystem/${encodeURIComponent(a.id)}`,
														{ method: "DELETE" },
													).catch(() => {});
													reloadEcosystem();
												}}
											/>
										))}
									</ContactGroup>
								)}
							</>
						);
					})()}
				</div>
			</div>

			{/* You — operator identity, backed by the personal agent row */}
			<PersonalAgentCard />


			<AddAgentModal
				open={showAdd}
				onClose={() => setShowAdd(false)}
				onAdded={() => reloadEcosystem()}
			/>
			<AgentInfoModal
				open={!!infoFor}
				onClose={() => setInfoFor(null)}
				agent={infoFor}
			/>
			<SettingsModal
				open={showSettings}
				onClose={() => setShowSettings(false)}
			/>
		</aside>
	);
}

/** Section heading + child rows. Header tells the operator what the
 * group is *for* (orchestrators vs single peers) so they don't have
 * to derive intent from the name. */
function ContactGroup({
	title,
	count,
	hint,
	children,
}: {
	title: string;
	count: number;
	hint: string;
	children: React.ReactNode;
}) {
	return (
		<div className="mb-2">
			<div className="flex items-center gap-1.5 px-3 pb-0.5 pt-2">
				<span className="text-[9px] uppercase tracking-[0.15em] text-fg-dim">
					{title}
				</span>
				<span className="rounded-full bg-slate-100 px-1.5 text-[9px] font-medium text-slate-600">
					{count}
				</span>
			</div>
			<div className="px-3 pb-1 text-[9px] italic text-fg-faint" title={hint}>
				{hint}
			</div>
			{children}
		</div>
	);
}

/** One contact line. Gateways and agents share the same shape but
 * lead with a different glyph so the operator can spot them at a
 * glance — sunflower for agents (our brand mark, one-bindu-per-row),
 * cobalt-tinted ⚡ for gateways (orchestrator role). */
function ContactRow({
	agent,
	kind,
	onInfo,
	onDelete,
}: {
	agent: EcosystemAgent;
	kind: "agent" | "gateway";
	onInfo: (a: EcosystemAgent) => void;
	onDelete: () => Promise<void> | void;
}) {
	const name = agent.agentCard?.name ?? agent.id;
	const didFromCard = pickDidFromCard(agent.agentCard);
	const realDid = agent.did?.id ?? didFromCard;
	const subline = realDid
		? shortDid(realDid)
		: agent.url ?? "no URL yet";
	return (
		<div
			className="group flex w-full items-center gap-2.5 rounded-md px-3 py-1.5 text-left hover:bg-(--color-row-hover)"
			title={realDid ?? agent.url ?? agent.id}
		>
			<span
				className={clsx(
					"flex h-6 w-6 shrink-0 items-center justify-center leading-none",
					kind === "gateway"
						? "rounded-md bg-blue-50 text-[12px] text-blue-700"
						: "text-[15px]",
				)}
				aria-hidden
			>
				{kind === "gateway" ? "⚡" : "🌻"}
			</span>
			<div className="min-w-0 flex-1">
				<div className="truncate text-[12px] text-fg">{name}</div>
				<div className="truncate text-[10px] text-fg-dim">{subline}</div>
			</div>
			<button
				type="button"
				onClick={(ev) => {
					ev.stopPropagation();
					onInfo(agent);
				}}
				title={kind === "gateway" ? "View gateway info" : "View agent info"}
				className="shrink-0 rounded p-1 text-fg-dim opacity-0 transition group-hover:opacity-100 hover:bg-blue-50 hover:text-blue-700"
			>
				<InfoIcon size={11} weight="bold" />
			</button>
			<button
				type="button"
				onClick={(ev) => {
					ev.stopPropagation();
					void onDelete();
				}}
				title={kind === "gateway" ? "Remove gateway" : "Remove contact"}
				className="shrink-0 rounded p-1 text-fg-dim opacity-0 transition group-hover:opacity-100 hover:bg-rose-50 hover:text-rose-700"
			>
				<TrashIcon size={11} weight="bold" />
			</button>
		</div>
	);
}

// ─── personal agent card ─────────────────────────────────────────────────
// Replaces the previous hardcoded `raahul@getbindu / did:bindu:raahul:0001`
// block. Now reads from the personal_agent row via the Zustand store:
//
//   me === undefined   → still hydrating (skeleton)
//   me === null        → no persona yet → "Create your agent" CTA
//   me.status alive    → green dot, DID, ⋯ menu (Stop / Edit / Logs)
//   me.status starting → amber dot + spinner
//   me.status down     → gray dot + "Start" button
//   me.status failed   → red dot + "Retry" button + last error hint
//
// Polls /api/me every 30s while the tab is visible so external state
// drift (agent crashed, was started from another terminal, etc.) shows
// up without a page reload.

function PersonalAgentCard() {
	const me = useUI((s) => s.me);
	const hydrateMe = useUI((s) => s.hydrateMe);
	const openWizard = useUI((s) => s.openWizard);

	// 30s heartbeat — same visibility-gated pattern as `useEcosystem`.
	useEffect(() => {
		const t = setInterval(() => {
			if (typeof document !== "undefined" && document.hidden) return;
			void hydrateMe();
		}, 30_000);
		const onVis = () => {
			if (!document.hidden) void hydrateMe();
		};
		document.addEventListener("visibilitychange", onVis);
		return () => {
			clearInterval(t);
			document.removeEventListener("visibilitychange", onVis);
		};
	}, [hydrateMe]);

	if (me === undefined) {
		return (
			<div className="mt-auto border-t border-(--color-border-soft) px-4 py-3">
				<div className="h-3 w-20 animate-pulse rounded bg-slate-200" />
				<div className="mt-1.5 h-2.5 w-32 animate-pulse rounded bg-slate-100" />
			</div>
		);
	}

	if (me === null) {
		return (
			<div className="mt-auto border-t border-(--color-border-soft) px-3 py-3">
				<button
					type="button"
					onClick={openWizard}
					className="flex w-full items-center justify-center gap-1.5 rounded-md border border-dashed border-(--color-cobalt) bg-(--color-cobalt-soft)/40 px-3 py-2 text-[12px] font-medium text-(--color-cobalt) transition hover:bg-(--color-cobalt-soft)"
				>
					<PlusIcon size={12} weight="bold" />
					Create your agent
				</button>
			</div>
		);
	}

	return <PersonalAgentAliveCard me={me} />;
}

function PersonalAgentAliveCard({ me }: { me: PersonalAgent }) {
	const hydrateMe = useUI((s) => s.hydrateMe);
	const openWizard = useUI((s) => s.openWizard);
	const setMe = useUI((s) => s.setMe);
	const [busy, setBusy] = useState<"spawning" | "stopping" | null>(null);
	const [menuOpen, setMenuOpen] = useState(false);
	const [errMsg, setErrMsg] = useState<string | null>(null);
	// Show-myself modal — reuses AgentInfoModal by feeding it a stub
	// EcosystemAgent with id="me". The modal then fetches the live
	// snapshot (agent card, DID doc, skills, health) just like it
	// would for any peer in Contacts.
	const [showSelf, setShowSelf] = useState<EcosystemAgent | null>(null);
	const menuRef = useRef<HTMLDivElement | null>(null);

	// Close the ⋯ menu on outside click.
	useEffect(() => {
		if (!menuOpen) return;
		function onDocClick(e: MouseEvent) {
			if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
		}
		document.addEventListener("mousedown", onDocClick);
		return () => document.removeEventListener("mousedown", onDocClick);
	}, [menuOpen]);

	const persona = me.persona as { name?: string };
	const personaName = persona.name ?? "agent";
	const status = me.status;
	const dotCls =
		status === "alive"
			? "bg-(--color-cobalt)"
			: status === "starting"
				? "bg-(--color-cobalt-soft) animate-pulse"
				: status === "failed"
					? "bg-rose-500"
					: "bg-slate-400";
	const statusLabel =
		status === "alive"
			? "alive"
			: status === "starting"
				? "starting…"
				: status === "configuring"
					? "not started"
					: status;

	async function start() {
		setBusy("spawning");
		setErrMsg(null);
		const r = await postJson<PersonalAgent>("/api/me/spawn", {});
		setBusy(null);
		if (!r.ok || !r.data) {
			setErrMsg(r.errMsg ?? "spawn failed");
			void hydrateMe();
			return;
		}
		setMe(r.data);
	}

	async function stop() {
		setBusy("stopping");
		setErrMsg(null);
		await postJson("/api/me/stop", {});
		setBusy(null);
		setMenuOpen(false);
		void hydrateMe();
	}

	return (
		<div className="relative mt-auto border-t border-(--color-border-soft) px-3 py-3">
			<div className="flex items-center gap-2">
				<span
					className={clsx("h-2 w-2 shrink-0 rounded-full", dotCls)}
					title={statusLabel}
					aria-label={`agent ${statusLabel}`}
				/>
				<div className="min-w-0 flex-1">
					<div className="truncate text-[12px] font-medium text-fg">
						{personaName}
					</div>
					<div
						className="truncate text-[10px] text-fg-dim"
						title={me.did ?? undefined}
					>
						{me.did ? shortDid(me.did) : "DID generated on start"}
					</div>
				</div>
				{status !== "alive" && status !== "starting" && (
					<button
						type="button"
						onClick={start}
						disabled={busy !== null}
						title="Start agent"
						className={clsx(
							"shrink-0 rounded-md px-2 py-1 text-[11px] font-medium shadow-sm transition",
							busy
								? "bg-slate-200 text-slate-400"
								: "bg-blue-700 text-white hover:bg-blue-800",
						)}
					>
						{busy === "spawning" ? (
							"…"
						) : (
							<span className="inline-flex items-center gap-1">
								<PlayIcon size={10} weight="fill" />
								Start
							</span>
						)}
					</button>
				)}
				<div ref={menuRef} className="relative">
					<button
						type="button"
						onClick={() => setMenuOpen((o) => !o)}
						title="More"
						className="shrink-0 rounded p-1 text-fg-dim transition hover:bg-slate-100 hover:text-fg"
					>
						<DotsThreeIcon size={14} weight="bold" />
					</button>
					{menuOpen && (
						<div className="absolute right-0 bottom-7 z-40 w-48 overflow-hidden rounded-md border border-(--color-border) bg-white text-[12px] shadow-lg">
							{/* Show myself — opens the same inspector we use for
							    peer agents. Only shown when the agent's row knows
							    a URL (i.e. it's been spawned at least once); the
							    /api/agents/me/live call needs that URL to fan out
							    to the live well-known endpoints. */}
							{me.url && (
								<button
									type="button"
									onClick={() => {
										setMenuOpen(false);
										setShowSelf({
											id: "me",
											url: me.url ?? undefined,
											did: me.did ? { id: me.did } : null,
											agentCard: {
												name:
													(me.persona as { name?: string }).name ?? "me",
											},
											source: "manual",
										});
									}}
									className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-fg transition hover:bg-slate-100"
								>
									<IdentificationCardIcon size={12} weight="duotone" />
									Show myself
								</button>
							)}
							<button
								type="button"
								onClick={() => {
									setMenuOpen(false);
									openWizard();
								}}
								className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-fg transition hover:bg-slate-100"
							>
								<PencilSimpleIcon size={12} weight="duotone" />
								Edit persona
							</button>
							{status === "alive" && (
								<button
									type="button"
									onClick={stop}
									disabled={busy === "stopping"}
									className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-rose-700 transition hover:bg-rose-50"
								>
									<StopIcon size={12} weight="fill" />
									{busy === "stopping" ? "Stopping…" : "Stop agent"}
								</button>
							)}
						</div>
					)}
				</div>
			</div>
			{errMsg && (
				<div className="mt-1.5 flex items-start gap-1 text-[10px] text-rose-700">
					<WarningIcon size={10} weight="fill" className="mt-0.5 shrink-0" />
					<span className="break-words">{errMsg}</span>
				</div>
			)}
			<AgentInfoModal
				open={!!showSelf}
				onClose={() => setShowSelf(null)}
				agent={showSelf}
			/>
		</div>
	);
}
