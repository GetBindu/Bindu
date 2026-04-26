---
id: 2026-04-18-timing-unsafe-token-compare
title: Bearer token comparison was timing-unsafe, recoverable byte-by-byte
severity: high
status: fixed
found: 2026-04-18
fixed: 2026-04-18
area: gateway/api
commit: 857197a
---

## Symptom

The gateway authenticated `/plan` requests with a bearer token compared
via `authConfig.tokens.includes(token)`. An attacker with network
access to the gateway could, with enough samples, recover a valid
token byte-by-byte via timing analysis.

No observable failure in normal operation — this is a latent
vulnerability that only matters when someone tries to exploit it. The
"bug" is the existence of the side channel, not any operator-visible
behavior.

## Root cause

`Array.prototype.includes` calls `===` for string comparison, which is
implemented as a character-by-character compare that short-circuits on
the first mismatching byte. Response time is a function of "how many
bytes of the guess matched before the mismatch." Over many samples,
the timing difference — though sub-microsecond per comparison —
becomes statistically measurable.

A second issue compounded the first: iterating `authConfig.tokens`
with a short-circuiting match could reveal which token in the list
was a prefix of the guess, not just whether any token matched. If the
attacker sees "no match" for `"aaa..."` and "no match but slower" for
`"dev..."`, they learn the first byte of the second configured token
is `d`.

Code in `gateway/src/api/plan-route.ts:40` (pre-fix):

```ts
if (!token || !authConfig.tokens.includes(token)) {
  return c.json({ error: "unauthorized" }, 401)
}
```

Mental model: "string equality is a cheap O(1) check." False for
security-sensitive comparisons — string equality is O(prefix length
until mismatch), and that length is exactly the information an
attacker wants.

## Fix

A constant-time validator (`validateBearerToken`) added to
`gateway/src/api/plan-route.ts`:

1. SHA-256 both the provided token and each configured token. Both
   sides become 32 bytes — removes length leak and satisfies
   `crypto.timingSafeEqual`'s equal-length requirement.
2. Run `timingSafeEqual` against every configured token, even after
   a match. Total wall time becomes O(tokens.length) regardless of
   which token matched or whether any did.
3. OR the per-token results into a single boolean at the end.

```ts
export function validateBearerToken(provided, validTokens) {
  if (validTokens.length === 0) return false
  const providedHash = createHash("sha256").update(provided, "utf8").digest()
  let matched = false
  for (const valid of validTokens) {
    const validHash = createHash("sha256").update(valid, "utf8").digest()
    if (timingSafeEqual(providedHash, validHash)) matched = true
  }
  return matched
}
```

Regression tests at `gateway/tests/api/bearer-token.test.ts` — six
cases covering correctness (match, mismatch, empty config, exact-match
semantics, length independence) and a loose timing-variance check
that runs 10k iterations each of a "byte-0 match" and a "byte-0
mismatch" guess and asserts their ratio stays under 3x. The old
`includes()` would fail that last test because character-by-character
compare amplifies the byte-depth difference over thousands of iterations.

See commit [857197a](../../commit/857197a).

## Why the tests didn't catch it

Timing attacks are not a correctness bug. All existing tests were
correctness tests: "given valid token, return 200; given invalid,
return 401." Those pass both before and after the fix. A test
suite that doesn't think about timing as a security property won't
catch the difference.

The library-level defense (`crypto.timingSafeEqual`) has existed in
Node since 6.x. The reason it wasn't used here is not technical —
it's that nobody wrote the code thinking about timing as an attack
surface. This is a common failure mode for "simple" auth code paths
where the comparison looks trivial.

Secondary reason: the `includes()` call was one line, in an obvious
place (the first step of the handler). It *felt* complete. Security
review culture — where someone specifically checks auth paths against
a checklist including "constant-time compare" — would have caught
it. Testing alone wouldn't.

## Class of bug — where else to watch

**"Secret comparison via short-circuiting equality"** — anywhere
user-supplied input is compared against a secret using `===`, `==`,
`.includes()`, `.startsWith()`, or hand-rolled string compare, the
code is timing-vulnerable. The fix is always the same: normalize to
equal-length bytes (hash if necessary), then use `timingSafeEqual`.

Specific other places to audit:

- **DID signature verification** ([bindu/identity/verify.ts](../../gateway/src/bindu/identity/verify.ts)):
  `verify()` delegates to `@noble/ed25519.verifyAsync`, which is
  constant-time by design. Safe.
- **Bindu `tasks/get` task-id matching** in the polling client: no
  user-supplied secret on this path, so not applicable.
- **Inbound webhook signatures** (Phase 5 payment processing): must
  use `timingSafeEqual` against whatever HMAC or signature format
  the provider expects. Treat any webhook secret as sensitive.
- **API key rotation / validation** if that feature lands: same rules
  apply. Even "is this an admin key?" prefix checks need care —
  compare hashes, not prefixes.

Broader rule: **any comparison where one side is attacker-supplied
and the other is a secret or access-control decision must be
constant-time.** It doesn't matter if the comparison is "only used in
auth" or "just a cache key lookup" — if the outcome gates access, the
timing is a side channel.

A meta-lesson from this bug: **`.includes()` on a secrets list is a
code smell.** The shape of "iterate and match" is fine for
non-sensitive data, but for secrets the loop itself becomes part of
the side channel (which entry matched, in which position). If you
see `secretsArray.includes(provided)` anywhere in a security-adjacent
path, it needs the hash + full-traversal pattern from this fix.
