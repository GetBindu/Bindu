import { createHash } from "node:crypto"

/**
 * Detect when the planner LLM is stuck calling the same tool with the same
 * input over and over. Mirrors opencode's `DOOM_LOOP_THRESHOLD = 3` in
 * `packages/opencode/src/session/processor.ts` — once three identical
 * tool+input pairs land in a row, the *next* call is rerouted to a synthetic
 * "stop retrying" message instead of being executed. The model sees the
 * message as a tool result and has a chance to pick a different approach or
 * finalize with what it has.
 *
 * This is the cheap safety net for a class of agentic-loop failures that
 * otherwise grind through `max_steps` (and the user's bill) without making
 * progress. It does NOT replace `max_steps` — that's the hard cap; this is
 * the early-exit ramp.
 *
 * Threshold rationale: 3 is "thrice is enemy action." Two is a legitimate
 * retry after a transient error; four-plus risks letting too many tokens
 * burn before we notice.
 */
export const DOOM_LOOP_THRESHOLD = 3

export type ToolCallRecord = {
	tool: string
	inputHash: string
}

/** Stable short hash of a tool's JSON-serializable input. Truncated to 16
 * hex chars because we only compare for equality across very recent calls
 * — full SHA-256 is overkill and noisier in logs. */
export function hashToolInput(input: unknown): string {
	return createHash("sha256")
		.update(JSON.stringify(input ?? null))
		.digest("hex")
		.slice(0, 16)
}

/** Returns true when the incoming `(tool, inputHash)` would be the
 * THRESHOLDth identical call in a row — i.e. the previous (THRESHOLD - 1)
 * records all match. Callers should treat `true` as "do NOT execute this
 * tool call; substitute a bail message." */
export function isDoomLoop(
	recent: ReadonlyArray<ToolCallRecord>,
	incoming: ToolCallRecord,
	threshold: number = DOOM_LOOP_THRESHOLD,
): boolean {
	if (threshold < 2) return false
	const needed = threshold - 1
	if (recent.length < needed) return false
	const tail = recent.slice(-needed)
	return tail.every(
		(r) => r.tool === incoming.tool && r.inputHash === incoming.inputHash,
	)
}

/** Synthetic tool result returned to the LLM in place of executing the
 * doom-looped call. Phrased as a directive the model can act on
 * (try a different input, switch tools, or summarize) rather than a
 * raw error, so the planner can recover within the same agentic turn. */
export function doomLoopBailMessage(
	tool: string,
	threshold: number = DOOM_LOOP_THRESHOLD,
): string {
	return [
		`[gateway:doom-loop] You have called the tool \`${tool}\` with identical input ${threshold} times in a row.`,
		"Previous attempts produced the same outcome — repeating will not help.",
		"Take a different approach: change the input, try a different tool, or finalize the answer with the information you already have.",
	].join(" ")
}
