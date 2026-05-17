import { useEffect, useState } from "react";
import clsx from "clsx";
import { GlobeIcon } from "@phosphor-icons/react";
import { Modal } from "./Modal";
import { FormError } from "./FormError";
import { ModalCloseButton } from "./ModalCloseButton";
import { postJson } from "~/lib/fetch";

interface Props {
	open: boolean;
	onClose: () => void;
	onAdded: () => void;
}

export function AddAgentModal({ open, onClose, onAdded }: Props) {
	const [url, setUrl] = useState("");
	const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
	const [errMsg, setErrMsg] = useState<string | null>(null);

	useEffect(() => {
		if (open) {
			setUrl("");
			setStatus("idle");
			setErrMsg(null);
		}
	}, [open]);

	const trimmed = url.trim();
	const canSubmit = /^https?:\/\//.test(trimmed) && status !== "loading";

	async function handleSubmit(e: React.FormEvent) {
		e.preventDefault();
		if (!canSubmit) return;
		setStatus("loading");
		setErrMsg(null);
		const r = await postJson("/api/ecosystem", { url: trimmed });
		if (!r.ok) {
			setStatus("error");
			setErrMsg(r.errMsg);
			return;
		}
		onAdded();
		onClose();
	}

	return (
		<Modal open={open} onClose={onClose}>
			<form
				onSubmit={handleSubmit}
				className="w-[480px] max-w-[92vw] rounded-lg border border-(--color-border) bg-white shadow-2xl"
			>
				<div className="flex items-center gap-2.5 border-b border-(--color-border-soft) px-5 py-3">
					<GlobeIcon size={18} weight="duotone" className="text-(--color-cobalt)" />
					<div className="flex-1">
						<h2 className="text-[14px] font-medium text-fg">Add agent to ecosystem</h2>
						<div className="text-[10px] text-fg-dim">
							Paste the agent's base URL. We'll fetch its agent card + DID document.
						</div>
					</div>
					<ModalCloseButton onClick={onClose} />
				</div>

				<div className="space-y-3 px-5 py-5">
					<div>
						<label className="block text-[10px] uppercase tracking-[0.15em] text-fg-dim">
							Agent URL
						</label>
						<input
							autoFocus
							type="text"
							value={url}
							onChange={(e) => setUrl(e.target.value)}
							placeholder="http://localhost:3773"
							className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-[13px] text-slate-900 placeholder:text-slate-400 outline-none transition focus:border-blue-700 focus:ring-2 focus:ring-blue-200"
						/>
						<div className="mt-1 text-[10px] text-fg-dim">
							Must serve <code>/.well-known/agent.json</code>.
						</div>
					</div>

					{status === "error" && <FormError message={errMsg} />}
				</div>

				<div className="flex items-center justify-end gap-2 border-t border-(--color-border-soft) bg-slate-50 px-5 py-3">
					<button
						type="button"
						onClick={onClose}
						className="rounded-md border border-(--color-border) bg-white px-3 py-1.5 text-[12px] text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
					>
						Cancel
					</button>
					<button
						type="submit"
						disabled={!canSubmit}
						className={clsx(
							"rounded-md px-3 py-1.5 text-[12px] font-medium shadow-sm transition",
							canSubmit
								? "bg-blue-700 text-white hover:bg-blue-800"
								: "bg-slate-200 text-slate-400",
						)}
					>
						{status === "loading" ? "Resolving…" : "Add agent"}
					</button>
				</div>
			</form>
		</Modal>
	);
}
