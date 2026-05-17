/** Standard rose-tinted error bar used inside modal/form bodies.
 *
 * Same shape we used to copy-paste into AddAgentModal, SettingsModal,
 * ComposeModal, and PersonalAgentWizard. Pass `null`/`undefined` to hide.
 *
 * The optional `className` slot is there for callers that need to add a
 * margin to position the bar (the modals use `mx-5 mb-3` to inset it
 * inside a card; AddAgentModal positions via its padded parent and
 * passes nothing). Default has no margin so plain placements still
 * render flush.
 */
export function FormError({
	message,
	className,
}: {
	message?: string | null;
	className?: string;
}) {
	if (!message) return null;
	return (
		<div
			className={`rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700${
				className ? ` ${className}` : ""
			}`}
		>
			✗ {message}
		</div>
	);
}
