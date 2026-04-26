---
id: 2026-04-26-hydra-token-cache-revocation-lag
title: Hydra introspection cache lets revoked tokens stay valid for up to 5 minutes
severity: medium
status: fixed
found: 2026-04-26
fixed: 2026-04-26
area: bindu/server/middleware/auth
commit: (this PR)
pr:
issue:
---

## Symptom

The Hydra middleware in
[`bindu/server/middleware/auth/hydra.py`](../../bindu/server/middleware/auth/hydra.py)
caches OAuth2 introspection results so that the same token does not
hit Hydra on every request. Pre-fix the cache TTL was hardcoded at
`CACHE_TTL_SECONDS = 300`, with no way to skip the cache or
invalidate an entry from outside.

That made revocation a delayed-action verb. An operator would
`POST /admin/oauth2/revoke` against Hydra (or call
`bindu.utils.http.tokens.revoke_token`), Hydra would mark the token
inactive, and Hydra-only callers would see the change immediately —
but every Bindu instance that had cached an `active=True` answer for
that token would keep accepting it for up to five minutes. For
sensitive operations (admin endpoints, payment capture, key rotation)
that window is too long: a leaked token reported within seconds still
gets several extra minutes of write access.

The blast radius scales with the number of Bindu instances. There is
no shared state between caches, so each pod that introspected the
token before the revocation has its own five-minute timer.

## Root cause

Two design gaps stacked on each other in
[`HydraMiddleware._validate_token`](../../bindu/server/middleware/auth/hydra.py):

1. **No scope-aware caching.** Every active token, regardless of how
   privileged it was, got the same 5-minute cache entry. A token
   carrying `payment:capture` was treated identically to one carrying
   `agent:read`. The cache made sense as a latency-vs-freshness
   tradeoff for the read path, but applying the same tradeoff to
   high-blast-radius scopes effectively raised revocation latency to
   `cache_ttl` for everything.
2. **No invalidation surface.** `HydraClient.revoke_token` posted to
   Hydra and returned a bool; nothing else fired. The middleware held
   the cache but exposed no method to drop entries, so even the
   instance that performed the revocation kept its own stale answer.

The settings file already carried a `cache_ttl` knob
([`HydraSettings.cache_ttl`](../../bindu/settings.py)) but the
middleware ignored it and used the module constant instead. Operators
who turned the knob down for high-risk deployments saw no change at
runtime — a separate dead-config bug that this fix also resolves.

## Fix

Three small changes, all in
[`bindu/server/middleware/auth/hydra.py`](../../bindu/server/middleware/auth/hydra.py):

- **Honour the configured TTL.** `__init__` now reads
  `auth_config.cache_ttl` (with a `CACHE_TTL_SECONDS` fallback) and
  stores it in `self._cache_ttl`. The setting is finally live.
- **Skip the cache for sensitive scopes.** `__init__` reads
  `auth_config.sensitive_scopes` (default `DEFAULT_SENSITIVE_SCOPES`
  = `{"admin", "agent:execute", "payment:capture", "key:rotate"}`).
  `_validate_token` calls `_is_cacheable` after introspection and
  returns the live result without writing to the cache when any
  scope intersects the sensitive set. Every request for a privileged
  token re-checks Hydra, so revocations take effect on the next call.
- **Local invalidation is now possible.** Two new methods:
  - `invalidate_token_cache(token)` — drops the entry for the given
    token. Returns whether anything was removed. Cheap, idempotent.
  - `revoke_token(token)` — wraps `hydra_client.revoke_token` and
    calls `invalidate_token_cache` afterwards. This is the
    recommended in-process revocation entry point; it ensures the
    cache cannot outlive the upstream revocation on this instance.

The matching setting lands in
[`HydraSettings.sensitive_scopes`](../../bindu/settings.py) so
operators can widen or narrow the bypass list per deployment without
patching code.

Eleven tests land alongside the fix in
[`tests/unit/server/middleware/test_hydra_token_cache.py`](../../tests/unit/server/middleware/test_hydra_token_cache.py):

- Sensitive scopes (`admin`, `payment:capture`) bypass the cache —
  every call hits Hydra, `_introspection_cache` stays empty.
- Non-sensitive scopes (`agent:read`) are cached as before — the
  fix doesn't penalize the common read path.
- Operator-overridden `sensitive_scopes` replace the defaults; an
  empty list disables the bypass entirely (regression-trap for
  anyone who sets the setting to `[]` thinking it means "use
  defaults").
- `invalidate_token_cache` removes a primed entry and returns True;
  returns False when nothing was cached.
- `revoke_token` calls Hydra and invalidates locally even when Hydra
  returns `False` (e.g. token already gone — local view should still
  match Hydra's view).
- A short `cache_ttl` (1 s) actually expires entries, proving the
  setting is no longer dead config.
- The default sensitive-scope set matches `DEFAULT_SENSITIVE_SCOPES`
  when no override is configured.

## What this does *not* fix

Cross-instance revocation propagation is still out of scope. If
instance A revokes a token and instance B has cached the
`active=True` answer, B keeps that cache until (a) the entry expires
or (b) something on B explicitly calls `invalidate_token_cache`.
Closing that gap requires either:

- A revocation channel (Redis pub/sub, Hydra webhook, or similar)
  that fans out invalidations to every instance.
- A revocation list with periodic polling.
- Aggressive cache TTLs on every instance — the operator knob now
  exists, but tuning it remains a deployment decision.

For the high-risk scopes named above the new fix is sufficient on its
own: those tokens never enter the cache, so cross-instance staleness
cannot accumulate. Lower-risk scopes (`agent:read`, `agent:write`)
still rely on TTL-based eviction, which is the intended tradeoff.

## Why the tests didn't catch it

There were no tests covering the cache lifecycle of `_validate_token`
at all — the existing
[`test_hydra_did_signature.py`](../../tests/unit/server/middleware/test_hydra_did_signature.py)
focuses on the DID layer that runs *after* introspection. The cache
was implicitly exercised by integration paths that always presented
freshly-issued tokens, so the "revoked but cached" state was never a
test case. Cache-vs-revocation bugs are particularly invisible to
unit tests that mock introspection: each call returns whatever the
mock says, so caching looks like a no-op.

The new test file pins down the cross-product of `sensitive vs not ×
cached vs invalidated × Hydra revoked vs not`. Future changes to the
cache code will have a clear failure signal.

## Class of bug — where else to watch

The shape here is **a cache that outlives the authority it caches**.
In any code path that caches a "yes you're allowed" verdict from an
external system, ask:

- What happens on the external system when the answer flips to "no"?
- Does the cache hear about it, or just wait out its TTL?
- For high-blast-radius answers (writes, money, keys), is the TTL
  actually low enough that "wait it out" is acceptable?

In this codebase the places most likely to hold the same shape:

- The DID public-key lookup in `HydraClient.get_public_key_from_client`
  isn't currently cached, but if a caller wraps it in one, the same
  question applies — a public-key rotation needs to invalidate the
  cache.
- Any future agent-trust or scope-mapping cache. If we ever add
  client-credentials → permission lookups with caching, the cache
  must skip privileged decisions or expose an explicit invalidation
  hook from day one.

The general rule: a security cache should either be unconditionally
short-TTL, or expose an invalidation surface, or skip entries with
high blast radius. Pre-fix this cache had none of the three.

## Follow-ups

- Cross-instance invalidation (Redis pub/sub, etc.) is the next
  iteration. Tracked separately if/when needed; the per-instance fix
  here removes the urgency for the common revocation path because
  privileged scopes already bypass cache.
- `HydraMiddleware._cache_locks` is allocated and populated by
  `_lazy_clean_cache` but never used as an actual lock. Latent code
  smell, not load-bearing for this fix; worth either wiring up
  per-token introspection locking or removing the dict entirely.
- `bindu.utils.http.tokens.revoke_token` is a free function that
  doesn't reach the running middleware instance. Operators revoking
  via that helper still leave caches stale on every instance,
  including their own. Documenting "use `HydraMiddleware.revoke_token`
  if available" is the short-term answer; long-term the helper should
  publish to the cross-instance invalidation channel mentioned above.
