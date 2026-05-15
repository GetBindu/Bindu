import { useEffect, useMemo } from "react";
import { useParams } from "react-router";
import clsx from "clsx";
import { PauseIcon, PlayIcon } from "@phosphor-icons/react";
import { events as mockEvents } from "~/data/mock";
import { useUI } from "~/state";
import { shortDid } from "~/lib/format";
import { ThreadList } from "./ThreadList";
import { ThreadView } from "./ThreadView";

export function StreamPanel() {
	const { agentId = "writer" } = useParams<{ agentId: string }>();
	const streamPaused = useUI((s) => s.streamPaused);
	const togglePause = useUI((s) => s.togglePause);
	const agents = useUI((s) => s.agents);
	const liveEvents = useUI((s) => s.liveEvents);
	const selectedThreadId = useUI((s) => s.selectedThreadId);
	const selectThread = useUI((s) => s.selectThread);

	const agent = agents.find((a) => a.id === agentId) ?? agents[0];

	// Clear the open thread when the user switches agents — a context_id
	// belongs to one agent's inbox, not another's.
	useEffect(() => {
		selectThread(null);
	}, [agentId, selectThread]);

	const agentEvents = useMemo(
		() =>
			[...liveEvents, ...mockEvents].filter((e) => e.agentId === agentId),
		[agentId, liveEvents],
	);

	return (
		<main className="flex min-w-0 flex-1 flex-col">
			<header className="flex items-center justify-between border-b border-[--color-border-soft] bg-[--color-panel] px-6 py-3">
				<div className="flex items-baseline gap-3">
					<h1 className="text-[14px] font-medium text-fg">{agent.name}</h1>
					<span className="text-[11px] text-fg-dim">{shortDid(agent.did)}</span>
				</div>
				<div className="flex items-center gap-3">
					<div className="flex items-center gap-1.5 text-[11px]">
						<span
							className={clsx(
								"inline-block h-1.5 w-1.5 rounded-full",
								streamPaused
									? "bg-yellow-400"
									: "live-pulse bg-[--color-cobalt]",
							)}
						/>
						<span className="text-fg-muted">
							{streamPaused ? "paused" : "live"}
						</span>
					</div>
					<button
						type="button"
						onClick={togglePause}
						className="flex items-center gap-1.5 rounded-md border border-[--color-border] bg-white px-2 py-1 text-[11px] text-fg-muted transition hover:border-[--color-cobalt] hover:text-[--color-cobalt]"
					>
						{streamPaused ? (
							<PlayIcon size={11} weight="fill" />
						) : (
							<PauseIcon size={11} weight="fill" />
						)}
						{streamPaused ? "Resume" : "Pause"}
					</button>
				</div>
			</header>

			{selectedThreadId ? (
				<ThreadView contextId={selectedThreadId} events={agentEvents} />
			) : (
				<div className="scrollbar flex-1 overflow-y-auto">
					<ThreadList events={agentEvents} />
				</div>
			)}
		</main>
	);
}
