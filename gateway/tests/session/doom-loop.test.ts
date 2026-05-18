import { describe, it, expect } from "vitest"
import {
	DOOM_LOOP_THRESHOLD,
	doomLoopBailMessage,
	hashToolInput,
	isDoomLoop,
	type ToolCallRecord,
} from "../../src/session/doom-loop"

/**
 * Guards the "we won't let the planner grind through max_steps re-calling
 * the same recipient with the same prompt" property. Mirror of opencode's
 * processor.ts:354-379 doom-loop check, ported to the gateway's tool
 * wrapper layer.
 */

const REC = (tool: string, inputHash: string): ToolCallRecord => ({
	tool,
	inputHash,
})

describe("hashToolInput", () => {
	it("is stable across calls with the same input", () => {
		expect(hashToolInput({ a: 1, b: "x" })).toBe(hashToolInput({ a: 1, b: "x" }))
	})

	it("differs when input differs", () => {
		expect(hashToolInput({ a: 1 })).not.toBe(hashToolInput({ a: 2 }))
	})

	it("handles nullish input without throwing", () => {
		expect(hashToolInput(null)).toBe(hashToolInput(undefined))
	})

	it("returns a 16-char hex string", () => {
		const h = hashToolInput({ x: 1 })
		expect(h).toMatch(/^[0-9a-f]{16}$/)
	})
})

describe("isDoomLoop", () => {
	const ham = REC("math.solve", "aaaa")

	it("does not fire on the first call", () => {
		expect(isDoomLoop([], ham)).toBe(false)
	})

	it("does not fire on the second identical call (threshold=3 means the third triggers)", () => {
		expect(isDoomLoop([ham], ham)).toBe(false)
	})

	it("fires on the third identical call in a row", () => {
		expect(isDoomLoop([ham, ham], ham)).toBe(true)
	})

	it("does not fire when the tool name differs", () => {
		const other = REC("joke.tell", "aaaa")
		expect(isDoomLoop([ham, ham], other)).toBe(false)
	})

	it("does not fire when the input hash differs", () => {
		const otherInput = REC("math.solve", "bbbb")
		expect(isDoomLoop([ham, ham], otherInput)).toBe(false)
	})

	it("only looks at the immediate tail (THRESHOLD-1 most recent)", () => {
		// Older identical entries with a different one in between should
		// not trip the detector.
		const interrupt = REC("joke.tell", "aaaa")
		expect(isDoomLoop([ham, ham, interrupt], ham)).toBe(false)
	})

	it("respects a custom threshold parameter", () => {
		expect(isDoomLoop([ham], ham, 2)).toBe(true)
		expect(isDoomLoop([], ham, 2)).toBe(false)
	})

	it("returns false when threshold is below the minimum sensible value", () => {
		expect(isDoomLoop([ham, ham], ham, 1)).toBe(false)
		expect(isDoomLoop([ham, ham], ham, 0)).toBe(false)
	})
})

describe("doomLoopBailMessage", () => {
	it("mentions the tool by name so the LLM can act on the specific case", () => {
		const msg = doomLoopBailMessage("math.solve")
		expect(msg).toContain("math.solve")
		expect(msg).toContain(String(DOOM_LOOP_THRESHOLD))
	})

	it("directs the model to change approach rather than just signal failure", () => {
		const msg = doomLoopBailMessage("math.solve")
		expect(msg.toLowerCase()).toMatch(/different|change|finalize/)
	})
})
