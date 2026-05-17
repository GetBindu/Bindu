import { useEffect, useMemo, useState } from "react";
import {
	InfoIcon,
	CopyIcon,
	CheckIcon,
	ArrowsClockwiseIcon,
	HeartbeatIcon,
	BrainIcon,
} from "@phosphor-icons/react";
import { Modal } from "./Modal";
import { ModalCloseButton } from "./ModalCloseButton";
import { isGateway as isGatewayByName } from "~/lib/agent-kind";
import type { EcosystemAgent } from "~/lib/api-types";

interface Props {
	open: boolean;
	onClose: () => void;
	agent: EcosystemAgent | null;
}

// Shape returned by GET /api/agents/:id/live — server bundles four
// upstream fetches and reports per-section success so the modal can
// render whatever came back. Mirrors the `settle()` helper there.
type Settled<T> =
	| { ok: true; data: T }
	| { ok: false; error: string };

interface LiveSnapshot {
	id: string;
	url: string;
	agentCard: Settled<Record<string, unknown>>;
	didDocument: Settled<Record<string, unknown>>;
	skills: Settled<Array<Record<string, unknown>>>;
	health: Settled<Record<string, unknown>>;
}

/** Read-only inspector for a contact.
 *
 * On open, hits the server-side `/api/agents/:id/live` proxy which
 * fans out to four upstream Bindu endpoints in parallel:
 *
 *   /.well-known/agent.json   — full agent card
 *   /.well-known/did.json     — DID document
 *   /agent/skills             — published skill summaries
 *   /health                   — liveness + readiness
 *
 * (See docs.getbindu.com — `/agent/skills` is the canonical skills
 * endpoint, the agent card's `skills` field is just a snapshot at
 * registration time and can lag behind.)
 *
 * Each section renders independently from the others — if /health is
 * down we still show skills, and vice versa. */
export function AgentInfoModal({ open, onClose, agent }: Props) {
	const [snap, setSnap] = useState<LiveSnapshot | null>(null);
	const [fetchState, setFetchState] = useState<
		"idle" | "loading" | "ok" | "error"
	>("idle");
	const [copied, setCopied] = useState(false);

	useEffect(() => {
		if (!open || !agent) {
			setSnap(null);
			setFetchState("idle");
			return;
		}
		let cancelled = false;
		setFetchState("loading");
		fetch(`/api/agents/${encodeURIComponent(agent.id)}/live`)
			.then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
			.then((j: LiveSnapshot) => {
				if (cancelled) return;
				setSnap(j);
				setFetchState("ok");
			})
			.catch(() => {
				if (cancelled) return;
				setFetchState("error");
			});
		return () => {
			cancelled = true;
		};
	}, [open, agent]);

	// Hooks must run on every render — keep `useMemo` above the
	// `if (!agent) return null` guard so the call order is stable.
	const health = snap?.health.ok ? snap.health.data : null;
	const isGateway = useMemo(() => {
		// Prefer the cryptographic signal: gateway /health includes
		// `runtime.planner`, agent /health does not.
		if (health && typeof health === "object") {
			const runtime = (health as { runtime?: { planner?: unknown } }).runtime;
			if (runtime && typeof runtime === "object" && runtime.planner)
				return true;
		}
		// Fall back to the name heuristic when /health is unreachable
		// (e.g. modal opened while the gateway is down).
		if (!agent) return false;
		return isGatewayByName(agent);
	}, [health, agent]);

	if (!agent) return null;
	const cardName =
		(snap?.agentCard.ok ? (snap.agentCard.data.name as string) : undefined) ??
		agent.agentCard?.name ??
		agent.id;
	const did = agent.did?.id ?? null;
	const subline = did ?? agent.url ?? agent.id;

	const skills =
		snap?.skills.ok && Array.isArray(snap.skills.data) ? snap.skills.data : [];

	// What goes into the JSON pane: prefer the live snapshot when we
	// have it (gives the operator a richer picture), otherwise fall
	// back to the cached row.
	const fullJson = snap ? JSON.stringify(snap, null, 2) : JSON.stringify(agent, null, 2);

	async function handleCopy() {
		try {
			await navigator.clipboard.writeText(fullJson);
			setCopied(true);
			setTimeout(() => setCopied(false), 1200);
		} catch {
			/* clipboard blocked — fail silent */
		}
	}

	return (
		<Modal open={open} onClose={onClose}>
			<div className="flex max-h-[88vh] w-[760px] max-w-[94vw] flex-col rounded-lg border border-slate-200 bg-white shadow-2xl">
				{/* Header */}
				<div className="flex items-center gap-2.5 border-b border-slate-100 px-5 py-3">
					<InfoIcon size={18} weight="duotone" className="text-blue-700" />
					<div className="min-w-0 flex-1">
						<h2 className="truncate text-[14px] font-medium text-slate-900">
							{cardName}
						</h2>
						<div className="truncate font-mono text-[10px] text-slate-500">
							{subline}
						</div>
					</div>
					<FetchStatus state={fetchState} />
					{/* Copy-everything button — same payload as the "Copy JSON"
					    one tucked in the Live snapshot section, but promoted to
					    the header so it's the first thing the operator sees.
					    Copies the live `/api/agents/:id/live` snapshot (card +
					    DID doc + skills + health) as one pretty-printed JSON
					    blob. Falls back to the cached agent row if the live
					    fetch hasn't finished. */}
					<button
						type="button"
						onClick={handleCopy}
						title="Copy full agent snapshot as JSON"
						className="flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
					>
						{copied ? (
							<>
								<CheckIcon size={12} weight="bold" />
								Copied
							</>
						) : (
							<>
								<CopyIcon size={12} weight="bold" />
								Copy
							</>
						)}
					</button>
					<ModalCloseButton onClick={onClose} />
				</div>

				<div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
					{/* Health pills */}
					<HealthSection state={fetchState} health={health} snap={snap} />

					{/* Capability section — gateways and agents have very
					    different surfaces, so we render different content
					    rather than show an empty Skills list for gateways
					    (they don't publish /agent/skills). */}
					{isGateway ? (
						<GatewayCapabilities state={fetchState} health={health} />
					) : (
						<SkillsSection
							state={fetchState}
							skills={skills}
							skillsError={
								snap && !snap.skills.ok ? snap.skills.error : null
							}
						/>
					)}

					{/* Full JSON */}
					<section>
						<div className="mb-2 flex items-center justify-between">
							<h3 className="text-[10px] uppercase tracking-[0.15em] text-slate-500">
								Live snapshot
								{snap && (
									<span className="ml-2 rounded bg-(--color-cobalt-soft) px-1.5 py-0.5 text-[9px] font-medium text-(--color-cobalt)">
										LIVE
									</span>
								)}
							</h3>
							<button
								type="button"
								onClick={handleCopy}
								className="flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
							>
								{copied ? (
									<>
										<CheckIcon size={11} weight="bold" />
										Copied
									</>
								) : (
									<>
										<CopyIcon size={11} weight="bold" />
										Copy JSON
									</>
								)}
							</button>
						</div>
						<PrettyJson source={fullJson} />
					</section>
				</div>
			</div>
		</Modal>
	);
}

function HealthSection({
	state,
	health,
	snap,
}: {
	state: "idle" | "loading" | "ok" | "error";
	health: Record<string, unknown> | null;
	snap: LiveSnapshot | null;
}) {
	if (state === "loading" && !snap) {
		return (
			<section>
				<h3 className="mb-2 text-[10px] uppercase tracking-[0.15em] text-slate-500">
					Health
				</h3>
				<div className="text-[12px] italic text-slate-500">
					Probing /health…
				</div>
			</section>
		);
	}
	if (!health) {
		return (
			<section>
				<h3 className="mb-2 text-[10px] uppercase tracking-[0.15em] text-slate-500">
					Health
				</h3>
				<div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-800">
					/health unreachable —{" "}
					{snap?.health.ok === false ? snap.health.error : "agent offline?"}
				</div>
			</section>
		);
	}
	const status = String(health.health ?? health.status ?? "unknown");
	const ready = health.ready === true;
	const uptime = typeof health.uptime_seconds === "number"
		? formatUptime(health.uptime_seconds as number)
		: null;
	const versionRaw = (health.version as Record<string, unknown> | undefined)?.version;
	const version =
		typeof versionRaw === "string" || typeof versionRaw === "number"
			? String(versionRaw)
			: undefined;
	const healthy = status.toLowerCase() === "healthy" || status.toLowerCase() === "ok";
	return (
		<section>
			<h3 className="mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-slate-500">
				<HeartbeatIcon size={11} weight="bold" />
				Health
			</h3>
			<div className="flex flex-wrap gap-2">
				<Pill
					tone={healthy ? "emerald" : "rose"}
					label={status}
					title="overall health"
				/>
				<Pill
					tone={ready ? "emerald" : "amber"}
					label={ready ? "ready" : "not ready"}
					title="readiness probe"
				/>
				{uptime && <Pill tone="slate" label={`up ${uptime}`} title="uptime" />}
				{version && (
					<Pill tone="slate" label={`v${version}`} title="version" />
				)}
			</div>
		</section>
	);
}

function SkillsSection({
	state,
	skills,
	skillsError,
}: {
	state: "idle" | "loading" | "ok" | "error";
	skills: Array<Record<string, unknown>>;
	skillsError: string | null;
}) {
	const isLoading = state === "loading";
	return (
		<section>
			<h3 className="mb-2 text-[10px] uppercase tracking-[0.15em] text-slate-500">
				Skills ({skills.length})
				<span className="ml-2 font-mono text-[9px] normal-case tracking-normal text-slate-400">
					GET /agent/skills
				</span>
			</h3>
			{isLoading ? (
				<div className="text-[12px] italic text-slate-500">
					Fetching skills…
				</div>
			) : skillsError ? (
				<div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-800">
					{skillsError}
				</div>
			) : skills.length === 0 ? (
				<div className="text-[12px] italic text-slate-500">
					This agent publishes no skills.
				</div>
			) : (
				<ul className="space-y-2">
					{skills.map((s, i) => (
						<SkillCard key={(s.id as string) ?? i} skill={s} index={i} />
					))}
				</ul>
			)}
		</section>
	);
}

/** Gateway-specific replacement for `SkillsSection`. Gateways don't
 * publish skills (they're orchestrators, not workers) — what's
 * meaningful instead is their planner config, recipe count, and
 * which trust mechanisms are wired up. All of this lives in the
 * `/health` response under `runtime.*`. */
function GatewayCapabilities({
	state,
	health,
}: {
	state: "idle" | "loading" | "ok" | "error";
	health: Record<string, unknown> | null;
}) {
	if (state === "loading" && !health) {
		return (
			<section>
				<h3 className="mb-2 text-[10px] uppercase tracking-[0.15em] text-slate-500">
					Planner
				</h3>
				<div className="text-[12px] italic text-slate-500">
					Reading /health…
				</div>
			</section>
		);
	}
	const runtime = (health as { runtime?: Record<string, unknown> } | null)
		?.runtime;
	const planner = runtime?.planner as Record<string, unknown> | undefined;
	const recipeCount = runtime?.recipe_count as number | undefined;
	const didSigning = runtime?.did_signing_enabled as boolean | undefined;
	const hydra = runtime?.hydra_integrated as boolean | undefined;
	const storage = runtime?.storage_backend as string | undefined;
	const bus = runtime?.bus_backend as string | undefined;

	return (
		<section className="space-y-3">
			<div>
				<h3 className="mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-slate-500">
					<BrainIcon size={11} weight="bold" />
					Planner
				</h3>
				{!planner ? (
					<div className="text-[12px] italic text-slate-500">
						No planner reported.
					</div>
				) : (
					<div className="grid grid-cols-2 gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
						<Field label="Model" value={String(planner.model ?? "?")} mono />
						<Field
							label="Provider"
							value={String(planner.provider ?? "?")}
						/>
						<Field
							label="Temperature"
							value={
								planner.temperature == null
									? "default"
									: String(planner.temperature)
							}
						/>
						<Field
							label="Max steps"
							value={
								planner.max_steps == null
									? "—"
									: String(planner.max_steps)
							}
						/>
					</div>
				)}
			</div>

			<div>
				<h3 className="mb-2 text-[10px] uppercase tracking-[0.15em] text-slate-500">
					Runtime
				</h3>
				<div className="flex flex-wrap gap-2">
					{typeof recipeCount === "number" && (
						<Pill
							tone="slate"
							label={`${recipeCount} ${recipeCount === 1 ? "recipe" : "recipes"}`}
							title="Planner playbooks loaded at boot"
						/>
					)}
					{typeof didSigning === "boolean" && (
						<Pill
							tone={didSigning ? "emerald" : "slate"}
							label={didSigning ? "DID signing on" : "DID signing off"}
							title="Whether did_signed peers can be reached"
						/>
					)}
					{typeof hydra === "boolean" && (
						<Pill
							tone={hydra ? "emerald" : "slate"}
							label={hydra ? "Hydra integrated" : "no Hydra"}
							title="OAuth2 token provider for did_signed peers"
						/>
					)}
					{storage && (
						<Pill tone="slate" label={`storage: ${storage}`} title="" />
					)}
					{bus && <Pill tone="slate" label={`bus: ${bus}`} title="" />}
				</div>
			</div>
		</section>
	);
}

function Field({
	label,
	value,
	mono,
}: {
	label: string;
	value: string;
	mono?: boolean;
}) {
	return (
		<div className="min-w-0">
			<div className="text-[9px] uppercase tracking-[0.15em] text-slate-500">
				{label}
			</div>
			<div
				className={`truncate text-[11px] text-slate-900 ${
					mono ? "font-mono" : ""
				}`}
				title={value}
			>
				{value}
			</div>
		</div>
	);
}

function SkillCard({
	skill,
	index,
}: {
	skill: Record<string, unknown>;
	index: number;
}) {
	const id = skill.id as string | undefined;
	const skillName =
		(skill.name as string) ?? id ?? `skill #${index + 1}`;
	const desc = skill.description as string | undefined;
	const version = skill.version as string | undefined;
	const tags = Array.isArray(skill.tags) ? (skill.tags as unknown[]) : [];
	return (
		<li className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
			<div className="flex items-baseline justify-between gap-2">
				<div className="text-[12px] font-medium text-slate-900">
					{skillName}
				</div>
				{version && (
					<span className="font-mono text-[10px] text-slate-500">
						v{version}
					</span>
				)}
			</div>
			{id && id !== skillName && (
				<div className="mt-0.5 font-mono text-[10px] text-slate-500">{id}</div>
			)}
			{desc && (
				<div className="mt-1 text-[11px] text-slate-600">{desc}</div>
			)}
			{tags.length > 0 && (
				<div className="mt-1.5 flex flex-wrap gap-1">
					{tags.map((t, j) => (
						<span
							key={j}
							className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-800"
						>
							{String(t)}
						</span>
					))}
				</div>
			)}
		</li>
	);
}

function FetchStatus({
	state,
}: {
	state: "idle" | "loading" | "ok" | "error";
}) {
	if (state === "loading") {
		return (
			<span className="flex items-center gap-1 text-[10px] text-slate-500">
				<ArrowsClockwiseIcon size={11} className="animate-spin" />
				probing
			</span>
		);
	}
	if (state === "error") {
		return (
			<span
				className="rounded bg-rose-50 px-1.5 py-0.5 text-[10px] text-rose-700"
				title="Server-side fetch failed."
			>
				offline
			</span>
		);
	}
	return null;
}

function Pill({
	tone,
	label,
	title,
}: {
	tone: "emerald" | "rose" | "amber" | "slate";
	label: string;
	title?: string;
}) {
	const cls = {
		emerald: "bg-(--color-cobalt-soft) text-(--color-cobalt) border-(--color-cobalt-soft)",
		rose: "bg-rose-50 text-rose-700 border-rose-200",
		amber: "bg-amber-50 text-amber-800 border-amber-200",
		slate: "bg-slate-50 text-slate-700 border-slate-200",
	}[tone];
	return (
		<span
			title={title}
			className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${cls}`}
		>
			{label}
		</span>
	);
}

function formatUptime(seconds: number): string {
	if (seconds < 60) return `${Math.floor(seconds)}s`;
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
	if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
	return `${Math.floor(seconds / 86400)}d`;
}

/** Inline JSON syntax highlighter — sky keys, emerald strings, amber
 * numbers, violet booleans/null. Order of alternatives in the regex
 * matters: keys must match before plain strings so the `:` lookahead
 * wins. Input is HTML-escaped first to neutralise any payload that
 * happens to contain `<` etc. */
function PrettyJson({ source }: { source: string }) {
	const html = useMemo(() => highlight(source), [source]);
	return (
		<pre className="scrollbar max-h-[400px] overflow-auto rounded-md border border-slate-200 bg-slate-950 p-4 font-mono text-[11px] leading-relaxed text-slate-200">
			<code
				className="block"
				// biome-ignore lint/security/noDangerouslySetInnerHtml: highlight() escapes input before adding spans.
				dangerouslySetInnerHTML={{ __html: html }}
			/>
		</pre>
	);
}

function escapeHtml(s: string): string {
	return s
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
}

function highlight(json: string): string {
	const escaped = escapeHtml(json);
	return escaped.replace(
		/("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|\b(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b/g,
		(_match, str, colon, lit, num) => {
			if (str && colon) {
				return `<span class="text-sky-300">${str}</span>${colon}`;
			}
			if (str) {
				return `<span class="text-emerald-300">${str}</span>`;
			}
			if (lit) {
				return `<span class="text-violet-300">${lit}</span>`;
			}
			if (num) {
				return `<span class="text-amber-300">${num}</span>`;
			}
			return _match;
		},
	);
}
