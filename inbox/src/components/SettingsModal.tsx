import { useEffect, useState } from "react";
import clsx from "clsx";
import {
	CheckCircleIcon,
	EyeIcon,
	EyeSlashIcon,
	GearIcon,
	TrashIcon,
} from "@phosphor-icons/react";
import { Modal } from "./Modal";
import { FormError } from "./FormError";
import { ModalCloseButton } from "./ModalCloseButton";
import { postJson } from "~/lib/fetch";
import type { MaskedSettings, SettingsField } from "~/lib/api-types";

interface Props {
	open: boolean;
	onClose: () => void;
}

/** Secrets the operator supplies once and the personal agent reads on
 * every spawn. The form is plain — each row is a labelled input with a
 * show/hide toggle. Saved values come back masked from the server and
 * the input goes empty (placeholder shows the mask) so the operator
 * can confirm "yes, it's there" without re-revealing the secret.  */
const FIELDS: Array<{
	id: SettingsField;
	label: string;
	hint: string;
	secret: boolean;
	placeholder: string;
}> = [
	{
		id: "openrouterApiKey",
		label: "OpenRouter API key",
		hint: "Used by the agno agent for LLM calls. Get one at openrouter.ai/keys.",
		secret: true,
		placeholder: "sk-or-v1-…",
	},
	{
		id: "openrouterModel",
		label: "OpenRouter model",
		hint: "Defaults to openai/gpt-5-mini. Any OpenRouter model id works.",
		secret: false,
		placeholder: "openai/gpt-5-mini",
	},
	{
		id: "pipedreamProjectId",
		label: "Pipedream Project ID",
		hint: "From your Pipedream Connect project settings. Publishable.",
		secret: false,
		placeholder: "proj_xxxxxxxxx",
	},
	{
		id: "pipedreamClientId",
		label: "Pipedream Client ID",
		hint: "OAuth client ID for token mint. Same project as above.",
		secret: true,
		placeholder: "client_xxxxxxxxx",
	},
	{
		id: "pipedreamClientSecret",
		label: "Pipedream Client Secret",
		hint: "OAuth client secret. Never sent back to the browser after save.",
		secret: true,
		placeholder: "sec_xxxxxxxxxxxxxxxx",
	},
	{
		id: "pipedreamEnvironment",
		label: "Pipedream environment",
		hint: "Defaults to `development`. Use `production` for live accounts.",
		secret: false,
		placeholder: "development",
	},
];

export function SettingsModal({ open, onClose }: Props) {
	const [saved, setSaved] = useState<MaskedSettings | null>(null);
	const [drafts, setDrafts] = useState<Record<SettingsField, string>>(
		emptyDrafts(),
	);
	const [reveal, setReveal] = useState<Record<SettingsField, boolean>>(
		emptyReveal(),
	);
	const [busy, setBusy] = useState<"loading" | "saving" | null>(null);
	const [errMsg, setErrMsg] = useState<string | null>(null);

	useEffect(() => {
		if (!open) return;
		setErrMsg(null);
		setDrafts(emptyDrafts());
		setBusy("loading");
		fetch("/api/settings")
			.then((r) => (r.ok ? r.json() : null))
			.then((j: MaskedSettings | null) => {
				setSaved(j);
				setBusy(null);
			})
			.catch((e) => {
				setErrMsg((e as Error).message);
				setBusy(null);
			});
	}, [open]);

	function setDraft(id: SettingsField, v: string) {
		setDrafts((d) => ({ ...d, [id]: v }));
	}

	async function saveAll() {
		const partial: Partial<Record<SettingsField, string>> = {};
		for (const k of Object.keys(drafts) as SettingsField[]) {
			const v = drafts[k];
			if (v.trim().length > 0) partial[k] = v.trim();
		}
		if (Object.keys(partial).length === 0) {
			onClose();
			return;
		}
		setBusy("saving");
		setErrMsg(null);
		const res = await postJson<MaskedSettings>("/api/settings", partial);
		setBusy(null);
		if (!res.ok || !res.data) {
			setErrMsg(res.errMsg ?? "save failed");
			return;
		}
		setSaved(res.data);
		setDrafts(emptyDrafts());
	}

	async function clearField(id: SettingsField) {
		setBusy("saving");
		setErrMsg(null);
		try {
			const r = await fetch(`/api/settings/${id}`, { method: "DELETE" });
			if (r.ok) {
				const j = (await r.json()) as MaskedSettings;
				setSaved(j);
				setDrafts((d) => ({ ...d, [id]: "" }));
			} else {
				setErrMsg(`HTTP ${r.status}`);
			}
		} catch (e) {
			setErrMsg((e as Error).message);
		}
		setBusy(null);
	}

	return (
		<Modal open={open} onClose={onClose}>
			<div className="flex w-[640px] max-w-[95vw] flex-col rounded-lg border border-(--color-border) bg-white shadow-2xl">
				<div className="flex items-center gap-2.5 border-b border-(--color-border-soft) px-5 py-3">
					<GearIcon size={18} weight="duotone" className="text-(--color-cobalt)" />
					<div className="flex-1">
						<h2 className="text-[14px] font-medium text-fg">Settings</h2>
						<div className="text-[10px] text-fg-dim">
							Stored in the comms database. Read by the personal agent on every
							spawn — restart the agent for changes to take effect.
						</div>
					</div>
					<ModalCloseButton onClick={onClose} />
				</div>

				<div className="max-h-[60vh] space-y-4 overflow-y-auto px-5 py-5">
					{FIELDS.map((f) => {
						const masked = saved?.[f.id] ?? null;
						const have = saved?.have[f.id] ?? false;
						const isRevealed = reveal[f.id];
						return (
							<div key={f.id}>
								<label className="flex items-center justify-between pb-1">
									<span className="text-[10px] uppercase tracking-[0.12em] text-fg-dim">
										{f.label}
									</span>
									{have && (
										<span className="inline-flex items-center gap-1 text-[10px] text-(--color-cobalt)">
											<CheckCircleIcon size={10} weight="fill" />
											Saved: {masked}
										</span>
									)}
								</label>
								<div className="flex items-stretch gap-1.5">
									<div className="relative flex-1">
										<input
											type={f.secret && !isRevealed ? "password" : "text"}
											value={drafts[f.id]}
											onChange={(e) => setDraft(f.id, e.target.value)}
											placeholder={have ? "(leave blank to keep)" : f.placeholder}
											className={clsx(
												"w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-[12px] text-slate-900 placeholder:text-slate-400 outline-none transition focus:border-blue-700 focus:ring-2 focus:ring-blue-200",
												f.secret && "pr-9",
											)}
											autoComplete="off"
											spellCheck={false}
										/>
										{f.secret && (
											<button
												type="button"
												onClick={() =>
													setReveal((r) => ({ ...r, [f.id]: !r[f.id] }))
												}
												title={isRevealed ? "Hide" : "Reveal"}
												className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-1 text-fg-dim transition hover:bg-slate-100 hover:text-fg"
											>
												{isRevealed ? (
													<EyeSlashIcon size={12} weight="duotone" />
												) : (
													<EyeIcon size={12} weight="duotone" />
												)}
											</button>
										)}
									</div>
									{have && (
										<button
											type="button"
											onClick={() => clearField(f.id)}
											disabled={busy === "saving"}
											title="Clear this field"
											className="shrink-0 rounded-md border border-(--color-border) bg-white px-2 text-fg-dim transition hover:border-rose-300 hover:text-rose-700"
										>
											<TrashIcon size={12} weight="bold" />
										</button>
									)}
								</div>
								<div className="mt-0.5 text-[10px] leading-snug text-fg-dim">
									{f.hint}
								</div>
							</div>
						);
					})}
				</div>

				<FormError message={errMsg} className="mx-5 mb-3" />

				<div className="flex items-center justify-between border-t border-(--color-border-soft) bg-slate-50 px-5 py-3">
					<div className="text-[10px] text-fg-dim">
						{saved?.updatedAt
							? `Last saved ${new Date(saved.updatedAt).toLocaleString()}`
							: "No values saved yet."}
					</div>
					<div className="flex items-center gap-2">
						<button
							type="button"
							onClick={onClose}
							className="rounded-md border border-(--color-border) bg-white px-3 py-1.5 text-[12px] text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={saveAll}
							disabled={busy !== null}
							className={clsx(
								"rounded-md px-3 py-1.5 text-[12px] font-medium shadow-sm transition",
								busy
									? "bg-slate-200 text-slate-400"
									: "bg-blue-700 text-white hover:bg-blue-800",
							)}
						>
							{busy === "saving" ? "Saving…" : "Save"}
						</button>
					</div>
				</div>
			</div>
		</Modal>
	);
}

function emptyDrafts(): Record<SettingsField, string> {
	return {
		openrouterApiKey: "",
		openrouterModel: "",
		pipedreamProjectId: "",
		pipedreamClientId: "",
		pipedreamClientSecret: "",
		pipedreamEnvironment: "",
	};
}

function emptyReveal(): Record<SettingsField, boolean> {
	return {
		openrouterApiKey: false,
		openrouterModel: false,
		pipedreamProjectId: false,
		pipedreamClientId: false,
		pipedreamClientSecret: false,
		pipedreamEnvironment: false,
	};
}
