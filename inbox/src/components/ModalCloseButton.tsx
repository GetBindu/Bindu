import { XIcon } from "@phosphor-icons/react";

/** Small "X" close button used in every modal header. Standardises the
 * icon size + hover treatment so a future tweak only touches one place. */
export function ModalCloseButton({
	onClick,
	className,
}: {
	onClick: () => void;
	className?: string;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			className={`rounded p-1 text-fg-dim transition hover:bg-slate-100 hover:text-fg${
				className ? ` ${className}` : ""
			}`}
		>
			<XIcon size={14} weight="bold" />
		</button>
	);
}
