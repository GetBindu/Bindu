import { describe, it, expect } from "vitest"
import { buildPriorTaskIdLookup } from "../../src/planner/task-continuity"
import type { MessageWithParts } from "../../src/session"
import type {
	AssistantMessageInfo,
	UserMessageInfo,
} from "../../src/session/message"
import type {
	CallID,
	MessageID,
	PartID,
	SessionID,
} from "../../src/session/schema"

/**
 * Guards the cross-turn task_id continuity property. The planner walks
 * loaded session history once per /plan call and pulls each peer's most
 * recent taskId so the next callPeer can chain via referenceTaskIds.
 */

const sid = "sess-test" as SessionID
const mid = (n: number): MessageID => `msg-${n}` as MessageID
const pid = (n: number): PartID => `part-${n}` as PartID
const cid = (n: number): CallID => `call-${n}` as CallID

function user(n: number): MessageWithParts {
	const info: UserMessageInfo = {
		id: mid(n),
		sessionID: sid,
		role: "user",
		time: { created: 1000 + n },
	}
	return { info, parts: [] }
}

function assistantWithToolCall(opts: {
	n: number
	tool: string
	peer?: string
	taskId?: string
	status?: "completed" | "error" | "pending"
}): MessageWithParts {
	const info: AssistantMessageInfo = {
		id: mid(opts.n),
		sessionID: sid,
		role: "assistant",
		modelID: "x",
		providerID: "x",
		agent: "planner",
		tokens: { input: 0, output: 0, total: 0, cache: { read: 0, write: 0 } },
		time: { created: 1000 + opts.n, completed: 1000 + opts.n + 1 },
	}
	const status = opts.status ?? "completed"
	const metadata =
		opts.peer !== undefined || opts.taskId !== undefined
			? {
					...(opts.peer !== undefined ? { peer: opts.peer } : {}),
					...(opts.taskId !== undefined ? { taskId: opts.taskId } : {}),
				}
			: undefined
	const part: import("../../src/session/message").Part =
		status === "completed"
			? {
					id: pid(opts.n),
					type: "tool" as const,
					callID: cid(opts.n),
					tool: opts.tool,
					state: {
						status: "completed" as const,
						input: { x: 1 },
						output: "ok",
						...(metadata ? { metadata } : {}),
						time: { start: 1, end: 2 },
					},
				}
			: status === "error"
				? {
						id: pid(opts.n),
						type: "tool" as const,
						callID: cid(opts.n),
						tool: opts.tool,
						state: {
							status: "error" as const,
							input: { x: 1 },
							error: "boom",
							time: { start: 1, end: 2 },
						},
					}
				: {
						id: pid(opts.n),
						type: "tool" as const,
						callID: cid(opts.n),
						tool: opts.tool,
						state: {
							status: "pending" as const,
							input: { x: 1 },
							time: { start: 1 },
						},
					}
	return { info, parts: [part] }
}

describe("buildPriorTaskIdLookup", () => {
	it("returns undefined when history is empty", () => {
		const lookup = buildPriorTaskIdLookup([])
		expect(lookup("math")).toBeUndefined()
	})

	it("returns the taskId for a peer with one prior completed call", () => {
		const history = [
			user(1),
			assistantWithToolCall({ n: 2, tool: "call_math_solve", peer: "math", taskId: "t-1" }),
		]
		const lookup = buildPriorTaskIdLookup(history)
		expect(lookup("math")).toBe("t-1")
	})

	it("returns the most recent taskId when the peer was called multiple times", () => {
		const history = [
			user(1),
			assistantWithToolCall({ n: 2, tool: "call_math_solve", peer: "math", taskId: "t-1" }),
			user(3),
			assistantWithToolCall({ n: 4, tool: "call_math_solve", peer: "math", taskId: "t-2" }),
		]
		const lookup = buildPriorTaskIdLookup(history)
		expect(lookup("math")).toBe("t-2")
	})

	it("tracks separate taskIds per peer", () => {
		const history = [
			user(1),
			assistantWithToolCall({ n: 2, tool: "call_math_solve", peer: "math", taskId: "t-math" }),
			user(3),
			assistantWithToolCall({ n: 4, tool: "call_joke_tell", peer: "joke", taskId: "t-joke" }),
		]
		const lookup = buildPriorTaskIdLookup(history)
		expect(lookup("math")).toBe("t-math")
		expect(lookup("joke")).toBe("t-joke")
		expect(lookup("nobody")).toBeUndefined()
	})

	it("ignores tool parts that did not complete successfully", () => {
		// Errored / pending parts have no metadata to harvest, so the
		// lookup falls through to undefined — first call gets a fresh task.
		const history = [
			user(1),
			assistantWithToolCall({
				n: 2,
				tool: "call_math_solve",
				peer: "math",
				taskId: "t-1",
				status: "error",
			}),
		]
		const lookup = buildPriorTaskIdLookup(history)
		expect(lookup("math")).toBeUndefined()
	})

	it("ignores completed tool parts that have no peer metadata", () => {
		// Defensive: a tool that wasn't stamped (recipe loader, future
		// internal tools) shouldn't accidentally pollute the lookup.
		const history = [
			user(1),
			assistantWithToolCall({ n: 2, tool: "load_recipe" }),
		]
		const lookup = buildPriorTaskIdLookup(history)
		expect(lookup("load_recipe")).toBeUndefined()
	})

	it("ignores user-role messages", () => {
		// Only assistant turns carry tool results in this gateway's schema;
		// scanning user turns would be a noop today, but the guard makes
		// future role additions safe.
		const history = [user(1), user(2)]
		const lookup = buildPriorTaskIdLookup(history)
		expect(lookup("math")).toBeUndefined()
	})
})
