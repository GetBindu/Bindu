import { describe, it, expect } from "vitest"
import { z } from "zod"
import { formatErrorDetail } from "../../src/api/plan-route"

/**
 * Regression guard for the /plan error body shape.
 *
 * Before: 400 responses carried `detail = (e as Error).message`, which for a
 * Zod failure is a JSON-stringified array of the schema's internal issue
 * records. Clients had to re-parse that blob to find the actual field name.
 *
 * Now: ZodError → `issues[]` of `{path, message}` + a human-friendly
 * `detail` summary. Non-Zod errors pass their message through unchanged so
 * the existing 500 callers aren't disturbed.
 */

const Schema = z.object({
  question: z.string().min(1, "question must be a non-empty string"),
  agents: z
    .array(
      z.object({
        name: z.string(),
        endpoint: z.string().url(),
      }),
    )
    .default([]),
})

describe("formatErrorDetail", () => {
  it("expands a ZodError into structured issues keyed by path", () => {
    const parsed = Schema.safeParse({ question: "", agents: [] })
    expect(parsed.success).toBe(false)
    if (parsed.success) return

    const out = formatErrorDetail(parsed.error)

    expect(out.issues).toBeDefined()
    expect(out.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          path: "question",
          message: expect.stringContaining("non-empty"),
        }),
      ]),
    )
    expect(out.detail).toContain("question")
    // Detail should be the human-friendly summary, not the raw JSON dump.
    expect(out.detail).not.toContain('"code"')
    expect(out.detail).not.toContain('"path"')
  })

  it("joins multi-field errors into one detail line", () => {
    const parsed = Schema.safeParse({
      question: "",
      agents: [{ name: "bad", endpoint: "not-a-url" }],
    })
    if (parsed.success) return

    const out = formatErrorDetail(parsed.error)
    expect(out.issues?.length).toBeGreaterThanOrEqual(2)
    expect(out.detail.split("; ").length).toBeGreaterThanOrEqual(2)
  })

  it("labels root-level errors as (root) in the path field", () => {
    const parsed = Schema.safeParse("not an object")
    if (parsed.success) return

    const out = formatErrorDetail(parsed.error)
    expect(out.issues?.[0]?.path).toBe("(root)")
  })

  it("passes Error.message through unchanged for non-Zod errors", () => {
    const out = formatErrorDetail(new Error("session: peer unreachable"))
    expect(out.detail).toBe("session: peer unreachable")
    expect(out.issues).toBeUndefined()
  })

  it("stringifies non-Error throwables", () => {
    const out = formatErrorDetail("some string")
    expect(out.detail).toBe("some string")
    expect(out.issues).toBeUndefined()
  })
})
