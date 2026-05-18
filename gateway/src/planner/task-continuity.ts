import type { MessageWithParts } from "../session"

/**
 * Per-recipient `task_id` continuity across turns within one `contextId`.
 *
 * Today every gateway → peer call mints a fresh `taskId`, so an agent like
 * `math_agent` sees turn 2 as a brand-new conversation even though it was
 * the same operator continuing the same thread. The opencode equivalent is
 * passing a prior subagent session's `task_id` back to `task()` so the
 * subagent resumes its own context (see opencode `task.txt` §3 + the
 * runtime path in `tool/task.ts`).
 *
 * In Bindu, the A2A protocol gives us two knobs:
 *   1. `taskId` — same id reuses the task (server-dependent; some agents
 *      reject when terminal). Risky.
 *   2. `referenceTaskIds` — new task that names its predecessor; the
 *      recipient can look up the prior task's artifacts. Safe across
 *      implementations.
 *
 * We use (2). This helper walks the loaded message history, finds the most
 * recent completed tool part for each peer, and pulls the stamped `taskId`
 * out of `state.metadata`. The planner threads the result into each
 * skill-tool so the next `callPeer` includes `referenceTaskIds: [prior]`.
 *
 * Why metadata-not-output: the tool output is a `<remote_content>` envelope
 * the LLM consumes; appending machine-readable taskIds there would either
 * leak to the user or confuse the model. Metadata is a side-channel the
 * gateway controls.
 */

export type PriorTaskIdLookup = (peerName: string) => string | undefined

/**
 * Build a per-peer "most recent taskId" lookup from a session's loaded
 * history. Walks oldest → newest; later entries shadow earlier ones so the
 * lookup returns the freshest task per peer at the end. Returns a function
 * (not a Map) so the planner can pass it to many `buildSkillTool` calls
 * without each one needing to clone or know the map's shape.
 */
export function buildPriorTaskIdLookup(
	history: ReadonlyArray<MessageWithParts>,
): PriorTaskIdLookup {
	const taskIdByPeer = new Map<string, string>()
	for (const msg of history) {
		if (msg.info.role !== "assistant") continue
		for (const part of msg.parts) {
			if (part.type !== "tool") continue
			if (part.state.status !== "completed") continue
			const meta = part.state.metadata as
				| { peer?: unknown; taskId?: unknown }
				| undefined
			if (!meta) continue
			const peer = typeof meta.peer === "string" ? meta.peer : undefined
			const taskId = typeof meta.taskId === "string" ? meta.taskId : undefined
			if (!peer || !taskId) continue
			taskIdByPeer.set(peer, taskId)
		}
	}
	return (peerName) => taskIdByPeer.get(peerName)
}
