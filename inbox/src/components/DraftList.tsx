import { FileIcon, TrashIcon } from "@phosphor-icons/react";
import { useUI } from "~/state";

export function DraftList() {
	const drafts = useUI((s) => s.drafts);
	const openComposeWith = useUI((s) => s.openComposeWith);
	const deleteDraft = useUI((s) => s.deleteDraft);

	if (drafts.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center px-6 py-24 text-center">
				<FileIcon size={48} weight="thin" className="mb-4 text-fg-dim" />
				<h3 className="mb-1 text-[15px] font-semibold text-fg">No drafts</h3>
				<p className="max-w-xs text-[12px] text-fg-muted">
					Compose a message and close the modal — it'll show up here.
				</p>
			</div>
		);
	}

	return (
		<div>
			{drafts.map((d) => {
				const dateStr = d.savedAt.slice(11, 19);
				const preview = d.text.length > 120 ? `${d.text.slice(0, 120)}…` : d.text;
				return (
					<button
						type="button"
						key={d.id}
						onClick={() => openComposeWith(d.id)}
						className="group flex w-full cursor-pointer items-center gap-3 border-b border-(--color-border-soft) px-4 py-2.5 text-left transition hover:bg-(--color-row-hover) md:px-6 md:py-3"
					>
						<div className="flex w-2.5 shrink-0 justify-center">
							<span className="text-(--color-cobalt)">
								<FileIcon size={13} weight="duotone" />
							</span>
						</div>
						<div className="min-w-0 flex-1">
							<div className="flex items-center gap-2">
								<span className="truncate text-[13px] font-semibold text-fg">
									To: {d.agentId}
								</span>
								<span className="rounded-full bg-rose-50 px-1.5 py-0.5 text-[10px] font-medium text-rose-700">
									Draft
								</span>
								<span className="ml-auto shrink-0 text-[11px] text-fg-dim">
									saved {dateStr}
								</span>
								<button
									type="button"
									onClick={(ev) => {
										ev.stopPropagation();
										deleteDraft(d.id);
									}}
									title="Delete draft"
									className="shrink-0 rounded p-1 text-fg-dim opacity-0 transition group-hover:opacity-100 hover:bg-rose-50 hover:text-rose-700"
								>
									<TrashIcon size={13} weight="bold" />
								</button>
							</div>
							<div className="mt-0.5 truncate text-[12px] text-fg-muted">
								{preview || "(empty body)"}
							</div>
						</div>
					</button>
				);
			})}
		</div>
	);
}
