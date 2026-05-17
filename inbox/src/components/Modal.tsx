import { useEffect, type ReactNode } from "react";

interface Props {
	open: boolean;
	onClose: () => void;
	children: ReactNode;
}

/** Backdrop + click-outside + escape-key shell shared by every modal.
 *
 * Three modals (Add agent, Compose, Register) used to roll their own
 * copy of this scaffolding. The form, header, and footer live inside
 * `children`, so each modal keeps full control of submit behaviour and
 * close semantics (compose, for example, auto-saves a draft on close).
 *
 * `onClose` fires for both the backdrop click and the Escape key — if
 * a caller needs to differentiate (e.g. "Save as draft on dismiss"),
 * it should run that logic inside the supplied handler. */
export function Modal({ open, onClose, children }: Props) {
	useEffect(() => {
		if (!open) return;
		function onKey(e: KeyboardEvent) {
			if (e.key === "Escape") onClose();
		}
		window.addEventListener("keydown", onKey);
		return () => window.removeEventListener("keydown", onKey);
	}, [open, onClose]);

	if (!open) return null;
	return (
		<div
			className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 backdrop-blur-sm"
			onClick={onClose}
		>
			<div onClick={(e) => e.stopPropagation()}>{children}</div>
		</div>
	);
}
