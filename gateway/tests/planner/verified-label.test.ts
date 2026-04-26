import { describe, it, expect } from "vitest"
import { computeVerifiedLabel } from "../../src/planner"

/**
 * Regression test for the "vacuous verified=yes" bug.
 *
 * Before this fix, the <remote_content> envelope flattened any positive
 * signatures.ok to verified="yes" — including the case where zero
 * artifacts were signed (ok is vacuously true when there's nothing to
 * fail). A planner LLM reading verified="yes" couldn't tell if a real
 * cryptographic check happened or if the agent simply isn't signing.
 *
 * The fix splits the happy path: "yes" now means "signed > 0 && all
 * verified" and a new "unsigned" label marks "verification ran but
 * nothing was signed." See BUGS_AND_KNOWN_ISSUES.md §Security and
 * correctness for the original issue.
 */

describe("computeVerifiedLabel", () => {
  it("returns 'unknown' when verification wasn't attempted (signatures null)", () => {
    expect(computeVerifiedLabel(null)).toBe("unknown")
  })

  it("returns 'yes' when every signed artifact verified", () => {
    expect(
      computeVerifiedLabel({ ok: true, signed: 2, verified: 2, unsigned: 0 }),
    ).toBe("yes")
  })

  it("returns 'yes' even when some artifacts were unsigned, as long as every signed one verified", () => {
    expect(
      computeVerifiedLabel({ ok: true, signed: 1, verified: 1, unsigned: 3 }),
    ).toBe("yes")
  })

  it("returns 'unsigned' (not 'yes') when no artifacts carried signatures — prevents the vacuous pass", () => {
    // This is the bug the fix addresses. Pre-fix: "yes". Post-fix: "unsigned".
    expect(
      computeVerifiedLabel({ ok: true, signed: 0, verified: 0, unsigned: 4 }),
    ).toBe("unsigned")
  })

  it("returns 'unsigned' on an empty artifact list too", () => {
    expect(
      computeVerifiedLabel({ ok: true, signed: 0, verified: 0, unsigned: 0 }),
    ).toBe("unsigned")
  })

  it("returns 'no' when at least one signed artifact failed verification", () => {
    expect(
      computeVerifiedLabel({ ok: false, signed: 2, verified: 1, unsigned: 0 }),
    ).toBe("no")
  })

  it("returns 'no' even when signed === verified if ok is false (defensive against callers mutating counts)", () => {
    // Shouldn't happen with the real Bindu client's output — ok follows
    // deterministically from counts — but if any future caller constructs
    // a signatures object by hand, `ok` is the authoritative field.
    expect(
      computeVerifiedLabel({ ok: false, signed: 1, verified: 1, unsigned: 0 }),
    ).toBe("no")
  })
})
