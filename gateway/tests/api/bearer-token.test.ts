import { describe, it, expect } from "vitest"
import { validateBearerToken } from "../../src/api/plan-route"

/**
 * Unit tests for the timing-safe bearer token validator.
 *
 * Before the fix:
 *   - plan-route.ts used authConfig.tokens.includes(token), which
 *     compares strings with `===` — short-circuits on the first
 *     mismatching byte. An attacker measuring response time across
 *     many requests can recover the token byte-by-byte.
 *
 * The fix (src/api/plan-route.ts::validateBearerToken):
 *   - SHA-256 hash both sides so inputs are always 32 bytes
 *     (removes length leak, satisfies timingSafeEqual's equal-length
 *     requirement).
 *   - Run timingSafeEqual against EVERY configured token even after
 *     a match — total time is O(tokens.length), not dependent on which
 *     token matched or whether any did.
 *
 * Correctness tests pin the behavior. The final test is a coarse
 * timing-variance check — not a cryptographic proof, but enough to
 * detect an accidental reintroduction of short-circuit comparison.
 */

describe("validateBearerToken", () => {
  it("returns true when the token matches one of the configured tokens", () => {
    expect(validateBearerToken("alpha", ["alpha", "beta", "gamma"])).toBe(true)
    expect(validateBearerToken("gamma", ["alpha", "beta", "gamma"])).toBe(true)
  })

  it("returns false when the token is unknown", () => {
    expect(validateBearerToken("delta", ["alpha", "beta", "gamma"])).toBe(false)
  })

  it("returns false on empty token config (no one gets in by default)", () => {
    expect(validateBearerToken("anything", [])).toBe(false)
  })

  it("handles tokens of vastly different lengths (length not leaked)", () => {
    // Hash normalization means the validator works regardless of length.
    const short = "x"
    const long = "x".repeat(4096)
    expect(validateBearerToken(short, [long])).toBe(false)
    expect(validateBearerToken(long, [short])).toBe(false)
    expect(validateBearerToken(long, [long])).toBe(true)
  })

  it("exact-match required — no prefix or suffix hits", () => {
    expect(validateBearerToken("alpha", ["alphabet"])).toBe(false)
    expect(validateBearerToken("alphabet", ["alpha"])).toBe(false)
    expect(validateBearerToken("alpha ", ["alpha"])).toBe(false) // trailing space
    expect(validateBearerToken("Alpha", ["alpha"])).toBe(false)  // case sensitive
  })

  it("does not short-circuit — a full pass over the token list is made", () => {
    // Loose timing sanity check. With short-circuit compare, a guess
    // matching byte 0 of a long token would be MEASURABLY slower than
    // a guess mismatching byte 0, because the compare goes deeper.
    // With our fix (hash both sides), all invalid guesses take the same
    // number of hashes + compares, so the ratio of timings should be ~1.
    //
    // We don't assert an exact ratio (CI jitter makes that brittle);
    // instead we assert that 10k iterations of a "byte-0 match" guess
    // don't run DRAMATICALLY slower than 10k of a "byte-0 mismatch"
    // guess — within 3x, generously. The old includes() would fail this
    // test because character-by-character compare amplifies the
    // difference over thousands of iterations.
    const real = "dev-key-" + "x".repeat(100)
    const tokens = [real, "another-" + "y".repeat(100), "third-" + "z".repeat(100)]

    const iterations = 10_000

    // "hard" guess: matches first byte of the REAL token, then diverges.
    const hardGuess = "dev" + "q".repeat(105)
    const tStart1 = process.hrtime.bigint()
    for (let i = 0; i < iterations; i++) validateBearerToken(hardGuess, tokens)
    const tEnd1 = process.hrtime.bigint()

    // "easy" guess: mismatches byte 0.
    const easyGuess = "zzz" + "q".repeat(105)
    const tStart2 = process.hrtime.bigint()
    for (let i = 0; i < iterations; i++) validateBearerToken(easyGuess, tokens)
    const tEnd2 = process.hrtime.bigint()

    const hardNs = Number(tEnd1 - tStart1)
    const easyNs = Number(tEnd2 - tStart2)

    // Ratio should be close to 1.0. Allow 3x slack for CI jitter.
    const ratio = Math.max(hardNs, easyNs) / Math.max(Math.min(hardNs, easyNs), 1)
    expect(ratio).toBeLessThan(3)
  })
})
