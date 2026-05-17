import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import clsx from "clsx";
import {
	PaperPlaneTiltIcon,
	TrashIcon,
	UsersThreeIcon,
	UserIcon,
	CheckCircleIcon,
	WarningIcon,
} from "@phosphor-icons/react";
import { useUI } from "~/state";
import { Modal } from "./Modal";
import { AgentPicker } from "./AgentPicker";
import { FormError } from "./FormError";
import { ModalCloseButton } from "./ModalCloseButton";
import { postJson } from "~/lib/fetch";
import { postSse } from "~/lib/sse";
import { OUTBOX_AGENT_ID } from "~/lib/constants";
import { shortDid } from "~/lib/format";
import type { EcosystemAgent, PersonalAgent } from "~/lib/api-types";

interface Props {
	open: boolean;
	onClose: () => void;
}

// One row in the live plan log. Status frames from /api/plan (before
// the upstream stream takes over) get their own row type so the UI can
// show "spawning gateway…" / "building catalog…" inline while the
// operator waits.
type PlanLogRow =
	| { kind: "status"; phase: string; meta?: Record<string, unknown> }
	| { kind: "task-started"; taskId: string; agent: string; skill: string }
	| { kind: "task-finished"; taskId: string; agent: string; state: string }
	| {
			kind: "task-artifact";
			taskId: string;
			agent: string;
			content: string;
	  }
	| { kind: "error"; message: string }
	| { kind: "done" };

// Human-readable label for status phases — keeps the UI copy out of
// the server's machine-readable phase names.
const PHASE_LABEL: Record<string, string> = {
	preparing: "Preparing…",
	"spawning-gateway": "Spinning up a gateway…",
	"gateway-ready": "Gateway ready",
	"building-catalog": "Loading agent skills…",
	planning: "Planning…",
};

// Human copy for non-fatal warnings the spawn returns. The plan still
// runs; these just flag a reduced capability so the operator knows
// why (e.g.) did_signed peers won't work.
const WARNING_LABEL: Record<string, string> = {
	"hydra-unreachable": "Hydra unreachable",
};
const WARNING_TOOLTIP: Record<string, string> = {
	"hydra-unreachable":
		"Your configured Hydra admin URL didn't respond. Gateway started without it — did_signed peers are disabled for this session. Auth:none peers (your local agents) still work.",
};

export function ComposeModal({ open, onClose }: Props) {
	const navigate = useNavigate();
	const composeDraftId = useUI((s) => s.composeDraftId);
	const drafts = useUI((s) => s.drafts);
	const saveDraft = useUI((s) => s.saveDraft);
	const deleteDraft = useUI((s) => s.deleteDraft);
	// Personal agent — used to render "Sending from <persona> <did>" so
	// the operator can see at a glance whether outbound is going to be
	// attributed to their real DID or the OPERATOR_DID fallback.
	const me = useUI((s) => s.me);

	const [agents, setAgents] = useState<EcosystemAgent[]>([]);
	// Selected agent ids — single id means direct A2A send, two or more
	// means we route through the gateway (comms auto-spawns one if
	// needed; operator doesn't have to think about it).
	const [selected, setSelected] = useState<string[]>([]);
	const [text, setText] = useState("");
	const [status, setStatus] = useState<
		"idle" | "sending" | "streaming" | "error" | "done"
	>("idle");
	const [errMsg, setErrMsg] = useState<string | null>(null);
	const [draftId, setDraftId] = useState<string | null>(null);
	const sentRef = useRef(false);

	// Plan-stream state — populated when we go through the gateway.
	const [planLog, setPlanLog] = useState<PlanLogRow[]>([]);
	const [planFinal, setPlanFinal] = useState("");
	// Latest pre-plan status phase ("spawning-gateway" etc.). Cleared
	// once the upstream gateway emits its first real frame.
	const [currentPhase, setCurrentPhase] = useState<string | null>(null);
	// Non-fatal warnings from gateway spawn — surfaced as small chips
	// in the plan trace, doesn't block the plan from running.
	const [gatewayWarnings, setGatewayWarnings] = useState<string[]>([]);

	useEffect(() => {
		if (!open) return;
		setStatus("idle");
		setErrMsg(null);
		setPlanLog([]);
		setPlanFinal("");
		setCurrentPhase(null);
		setGatewayWarnings([]);
		sentRef.current = false;

		const draftToLoad = composeDraftId
			? drafts.find((d) => d.id === composeDraftId)
			: null;
		setDraftId(draftToLoad?.id ?? null);
		setText(draftToLoad?.text ?? "");

		fetch("/api/ecosystem")
			.then((r) => (r.ok ? r.json() : []))
			.then((j: EcosystemAgent[]) => {
				const filtered = j.filter((a) => a.id !== OUTBOX_AGENT_ID);
				setAgents(filtered);
				if (draftToLoad?.agentId) {
					setSelected([draftToLoad.agentId]);
				} else {
					setSelected([]);
				}
			})
			.catch(() => {});
	}, [open, composeDraftId, drafts]);

	const saveOnClose = () => {
		if (sentRef.current) return;
		const trimmed = text.trim();
		if (!trimmed || selected.length === 0) {
			if (draftId) deleteDraft(draftId);
			return;
		}
		// Drafts still carry a single agentId — only the first pick
		// persists. Multi-recipient draft support is a phase-2 problem.
		const id = draftId ?? crypto.randomUUID();
		saveDraft({
			id,
			agentId: selected[0],
			text: trimmed,
			savedAt: new Date().toISOString(),
		});
	};

	function handleCloseClick() {
		if (status === "streaming" || status === "done" || status === "sending") {
			sentRef.current = true;
			onClose();
			return;
		}
		saveOnClose();
		onClose();
	}

	function handleDiscard() {
		if (draftId) deleteDraft(draftId);
		sentRef.current = true;
		onClose();
	}

	const isMulti = selected.length >= 2;
	const canSubmit = useMemo(() => {
		if (selected.length === 0 || text.trim().length === 0) return false;
		return status === "idle" || status === "error";
	}, [selected, text, status]);

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault();
		if (!canSubmit) return;
		setErrMsg(null);

		if (!isMulti) {
			// Single-agent path — direct A2A.
			setStatus("sending");
			const r = await postJson("/api/compose", {
				agentId: selected[0],
				text: text.trim(),
			});
			if (!r.ok) {
				setStatus("error");
				setErrMsg(r.errMsg);
				return;
			}
			if (draftId) deleteDraft(draftId);
			sentRef.current = true;
			navigate("/sent");
			onClose();
			return;
		}

		// Multi-agent — through the gateway. /api/plan streams status
		// frames before the planner kicks in (preparing, spawning-
		// gateway, building-catalog, planning) and then forwards the
		// gateway's SSE verbatim. We don't have to know whether a
		// gateway exists; the server figures it out.
		setStatus("streaming");
		setPlanLog([]);
		setPlanFinal("");
		setCurrentPhase("preparing");
		try {
			const res = await postSse(
				"/api/plan",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						question: text.trim(),
						agentIds: selected,
					}),
				},
				(ev) => handleSseEvent(ev),
			);
			if (!res.ok) {
				const j = await res.json().catch(() => ({}));
				setStatus("error");
				setErrMsg(j.detail ?? j.error ?? `HTTP ${res.status}`);
				return;
			}
			if (draftId) deleteDraft(draftId);
			setStatus("done");
			sentRef.current = true;
		} catch (err) {
			setStatus("error");
			setErrMsg((err as Error).message);
		}
	}

	function handleSseEvent(ev: { type: string; data: unknown }) {
		const d = (ev.data ?? {}) as Record<string, unknown>;
		// "status" frames come from comms (pre-planner). Track the
		// latest as currentPhase so the UI can show "Spinning up a
		// gateway…" without spamming the log.
		if (ev.type === "status") {
			const phase = String(d.phase ?? "");
			if (phase) setCurrentPhase(phase);
			if (Array.isArray(d.warnings) && d.warnings.length > 0) {
				setGatewayWarnings((prev) => [
					...prev,
					...(d.warnings as string[]),
				]);
			}
			return;
		}
		// Once we see any real planner event, clear the pre-plan phase
		// — the upstream's own progress takes over.
		if (
			ev.type === "session" ||
			ev.type === "plan" ||
			ev.type === "task.started" ||
			ev.type === "text.delta"
		) {
			setCurrentPhase(null);
		}

		if (ev.type === "task.started") {
			setPlanLog((prev) => [
				...prev,
				{
					kind: "task-started",
					taskId: String(d.task_id ?? ""),
					agent: String(d.agent ?? "?"),
					skill: String(d.skill ?? "?"),
				},
			]);
		} else if (ev.type === "task.artifact") {
			setPlanLog((prev) => [
				...prev,
				{
					kind: "task-artifact",
					taskId: String(d.task_id ?? ""),
					agent: String(d.agent ?? "?"),
					content: String(d.content ?? ""),
				},
			]);
		} else if (ev.type === "task.finished") {
			setPlanLog((prev) => [
				...prev,
				{
					kind: "task-finished",
					taskId: String(d.task_id ?? ""),
					agent: String(d.agent ?? "?"),
					state: String(d.state ?? "completed"),
				},
			]);
		} else if (ev.type === "text.delta") {
			const delta = typeof d.delta === "string" ? d.delta : "";
			if (delta) setPlanFinal((prev) => prev + delta);
		} else if (ev.type === "error") {
			setPlanLog((prev) => [
				...prev,
				{ kind: "error", message: String(d.message ?? "Unknown error") },
			]);
			setCurrentPhase(null);
		} else if (ev.type === "done") {
			setPlanLog((prev) => [...prev, { kind: "done" }]);
			setCurrentPhase(null);
		}
	}

	const showStream = status === "streaming" || status === "done";

	return (
		<Modal open={open} onClose={handleCloseClick}>
			<form
				onSubmit={handleSubmit}
				className="flex max-h-[88vh] w-[640px] max-w-[94vw] flex-col rounded-lg border border-(--color-border) bg-white shadow-2xl"
			>
				<div className="flex items-center gap-2.5 border-b border-(--color-border-soft) px-5 py-3">
					<PaperPlaneTiltIcon
						size={18}
						weight="duotone"
						className="text-(--color-cobalt)"
					/>
					<div className="flex-1">
						<h2 className="text-[14px] font-medium text-fg">
							{showStream
								? "Request in progress"
								: draftId
									? "Resume draft"
									: "New request"}
						</h2>
						<div className="text-[10px] text-fg-dim">
							{isMulti
								? `Multi-agent — coordinated across ${selected.length} agents.`
								: "Send a message to an agent."}
						</div>
					</div>
					<ModalCloseButton onClick={handleCloseClick} />
				</div>

				<div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
					{showStream ? (
						<PlanStream
							log={planLog}
							finalText={planFinal}
							done={status === "done"}
							currentPhase={currentPhase}
							warnings={gatewayWarnings}
						/>
					) : (
						<ComposeForm
							agents={agents}
							selected={selected}
							onChange={setSelected}
							text={text}
							onTextChange={setText}
							errMsg={errMsg}
						/>
					)}
				</div>

				{/* From-DID strip — Phase 5. Tells the operator whose
				    identity this outbound message will carry. Green when
				    we're sending from their personal agent's real DID,
				    amber when we're falling back to the operator
				    placeholder (peer-side trust suffers in that case). */}
				{!showStream && <FromDidStrip me={me} />}
				<div className="flex items-center justify-between gap-2 border-t border-(--color-border-soft) bg-slate-50 px-5 py-3">
					{!showStream && draftId ? (
						<button
							type="button"
							onClick={handleDiscard}
							className="flex items-center gap-1.5 rounded-md border border-(--color-border) bg-white px-3 py-1.5 text-[12px] text-rose-700 transition hover:border-rose-300 hover:bg-rose-50"
						>
							<TrashIcon size={11} weight="bold" />
							Discard draft
						</button>
					) : (
						<span />
					)}
					<div className="flex items-center gap-2">
						{showStream ? (
							<button
								type="button"
								onClick={() => {
									sentRef.current = true;
									navigate("/sent");
									onClose();
								}}
								className="rounded-md border border-(--color-border) bg-white px-3 py-1.5 text-[12px] text-fg-muted transition hover:border-blue-700 hover:text-blue-700"
							>
								{status === "done" ? "Open in Sent" : "Close"}
							</button>
						) : (
							<>
								<button
									type="button"
									onClick={handleCloseClick}
									className="rounded-md border border-(--color-border) bg-white px-3 py-1.5 text-[12px] text-fg-muted transition hover:border-blue-700 hover:text-blue-700"
								>
									{text.trim() ? "Save & close" : "Cancel"}
								</button>
								<button
									type="submit"
									disabled={!canSubmit}
									className={clsx(
										"flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[12px] font-medium shadow-sm transition",
										canSubmit
											? "bg-blue-700 text-white hover:bg-blue-800"
											: "bg-slate-200 text-slate-400",
									)}
								>
									{isMulti ? (
										<UsersThreeIcon size={12} weight="bold" />
									) : (
										<UserIcon size={12} weight="bold" />
									)}
									{status === "sending"
										? "Sending…"
										: isMulti
											? "Send to all"
											: selected.length === 1
												? "Send request"
												: "Pick a recipient"}
								</button>
							</>
						)}
					</div>
				</div>
			</form>
		</Modal>
	);
}

function ComposeForm({
	agents,
	selected,
	onChange,
	text,
	onTextChange,
	errMsg,
}: {
	agents: EcosystemAgent[];
	selected: string[];
	onChange: (ids: string[]) => void;
	text: string;
	onTextChange: (s: string) => void;
	errMsg: string | null;
}) {
	return (
		<>
			<div>
				<label className="block text-[10px] uppercase tracking-[0.15em] text-fg-dim">
					To
				</label>
				{agents.length === 0 ? (
					<div className="mt-1.5 rounded-md border border-dashed border-(--color-border) bg-slate-50 px-3 py-2 text-[12px] text-fg-dim">
						No agents in your ecosystem yet. Add one from the sidebar first.
					</div>
				) : (
					<div className="mt-1.5">
						<AgentPicker
							agents={agents}
							selected={selected}
							onChange={onChange}
						/>
					</div>
				)}
			</div>

			<div>
				<label className="block text-[10px] uppercase tracking-[0.15em] text-fg-dim">
					Body
				</label>
				<textarea
					value={text}
					onChange={(e) => onTextChange(e.target.value)}
					placeholder={
						selected.length >= 2
							? "What should the planner achieve using these agents?"
							: "Type the request body…"
					}
					rows={5}
					className="mt-1.5 w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-[13px] text-slate-900 placeholder:text-slate-400 outline-none transition focus:border-blue-700 focus:ring-2 focus:ring-blue-200"
				/>
				<div className="mt-1 text-[10px] text-fg-dim">
					{selected.length >= 2
						? "We'll plan across these agents and stream results back."
						: "Closing without sending saves a draft."}
				</div>
			</div>

			<FormError message={errMsg} />
		</>
	);
}

function PlanStream({
	log,
	finalText,
	done,
	currentPhase,
	warnings,
}: {
	log: PlanLogRow[];
	finalText: string;
	done: boolean;
	currentPhase: string | null;
	warnings: string[];
}) {
	const phaseLabel = currentPhase ? PHASE_LABEL[currentPhase] ?? currentPhase : null;
	return (
		<div className="space-y-4">
			{phaseLabel && !done && (
				<div className="flex items-center gap-2 rounded-md border border-blue-100 bg-blue-50 px-3 py-2 text-[12px] text-blue-900">
					<span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-600" />
					{phaseLabel}
				</div>
			)}
			{warnings.length > 0 && (
				<div className="flex flex-wrap items-center gap-1.5">
					{warnings.map((w) => (
						<span
							key={w}
							className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] text-amber-800"
							title={WARNING_TOOLTIP[w] ?? w}
						>
							<WarningIcon size={9} weight="bold" />
							{WARNING_LABEL[w] ?? w}
						</span>
					))}
				</div>
			)}
			<section>
				<h3 className="mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-[0.15em] text-slate-500">
					{done ? (
						<CheckCircleIcon
							size={12}
							weight="fill"
							className="text-(--color-cobalt)"
						/>
					) : (
						<span className="inline-block h-2 w-2 animate-pulse rounded-full bg-(--color-cobalt)" />
					)}
					Plan trace
				</h3>
				{log.length === 0 ? (
					<div className="text-[12px] italic text-slate-500">
						{phaseLabel ?? "Waiting for the planner…"}
					</div>
				) : (
					<ul className="space-y-1.5">
						{log.map((row, i) => (
							<PlanLogItem key={i} row={row} />
						))}
					</ul>
				)}
			</section>

			{finalText && (
				<section>
					<h3 className="mb-2 text-[10px] uppercase tracking-[0.15em] text-slate-500">
						Answer
					</h3>
					<div className="whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 px-3 py-2.5 text-[12px] leading-relaxed text-slate-900">
						{finalText}
						{!done && (
							<span className="ml-0.5 inline-block h-3 w-1.5 animate-pulse bg-slate-400 align-middle" />
						)}
					</div>
				</section>
			)}
		</div>
	);
}

function PlanLogItem({ row }: { row: PlanLogRow }) {
	if (row.kind === "status") {
		return (
			<li className="text-[10px] italic text-slate-500">
				{PHASE_LABEL[row.phase] ?? row.phase}
			</li>
		);
	}
	if (row.kind === "task-started") {
		return (
			<li className="flex items-center gap-2 text-[11px] text-slate-600">
				<span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-blue-600" />
				<span className="text-slate-900">{row.agent}</span>
				<span className="font-mono text-slate-500">· {row.skill}</span>
				<span className="text-slate-400">running…</span>
			</li>
		);
	}
	if (row.kind === "task-finished") {
		const ok = row.state === "completed";
		return (
			<li className="flex items-center gap-2 text-[11px]">
				{ok ? (
					<CheckCircleIcon
						size={12}
						weight="fill"
						className="text-(--color-cobalt)"
					/>
				) : (
					<WarningIcon size={12} weight="fill" className="text-rose-600" />
				)}
				<span className="text-slate-900">{row.agent}</span>
				<span className={ok ? "text-(--color-cobalt)" : "text-rose-700"}>
					{row.state}
				</span>
			</li>
		);
	}
	if (row.kind === "task-artifact") {
		const inner = row.content.replace(
			/^<remote_content[^>]*>([\s\S]*?)<\/remote_content>\s*$/,
			"$1",
		);
		return (
			<li className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
				<div className="mb-1 flex items-center gap-1.5 text-[10px] text-slate-500">
					<span className="font-medium text-slate-700">{row.agent}</span>
					<span>returned</span>
				</div>
				<div className="whitespace-pre-wrap text-[11px] text-slate-700">
					{inner.length > 600 ? `${inner.slice(0, 600)}…` : inner}
				</div>
			</li>
		);
	}
	if (row.kind === "error") {
		return (
			<li className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
				✗ {row.message}
			</li>
		);
	}
	if (row.kind === "done") {
		return (
			<li className="flex items-center gap-2 text-[11px] text-(--color-cobalt)">
				<CheckCircleIcon size={12} weight="fill" />
				Done
			</li>
		);
	}
	return null;
}

/** Tells the operator whose DID will be stamped on outbound. Three
 * states:
 *
 *   alive + did   → green, "Sending from <persona> · did:bindu:..."
 *   no agent yet  → amber, "No personal agent — peer will see operator DID"
 *   agent down    → amber, "Agent <persona> is down — start it for signed traffic"
 *
 * Kept in the same file as ComposeModal because it's the only consumer
 * and the copy depends on the modal's surrounding UI vocabulary. */
function FromDidStrip({ me }: { me: PersonalAgent | null | undefined }) {
	if (me === undefined) return null;
	const personaName =
		me && typeof (me.persona as { name?: string }).name === "string"
			? (me.persona as { name: string }).name
			: null;
	const alive = me?.status === "alive" && !!me.did;

	if (alive && me.did) {
		return (
			<div
				className="flex items-center justify-between gap-3 border-t border-(--color-border-soft) bg-(--color-cobalt-soft)/40 px-5 py-1.5 text-[10px]"
				title={`Outbound will carry from_did=${me.did}`}
			>
				<div className="flex items-center gap-1.5 text-(--color-cobalt)">
					<CheckCircleIcon size={10} weight="fill" />
					<span className="font-medium">Sending from</span>
					<span className="text-fg">{personaName ?? "you"}</span>
				</div>
				<code className="truncate text-fg-dim" title={me.did}>
					{shortDid(me.did, 8)}
				</code>
			</div>
		);
	}

	const reason = !me
		? "No personal agent yet"
		: me.status === "starting"
			? `${personaName ?? "Agent"} is starting…`
			: `${personaName ?? "Agent"} is ${me.status}`;
	return (
		<div className="flex items-center gap-1.5 border-t border-(--color-border-soft) bg-amber-50/60 px-5 py-1.5 text-[10px] text-amber-800">
			<WarningIcon size={10} weight="fill" />
			<span>
				<span className="font-medium">{reason}</span>
				<span className="text-amber-700">
					{" — peer will see operator DID fallback. Start your agent for signed traffic."}
				</span>
			</span>
		</div>
	);
}
