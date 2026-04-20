/**
 * Bindu identity module.
 *
 * Importing this file (or anything re-exported from it) runs the
 * @noble/ed25519 v2 sha512 hook bootstrap as a side effect. Phase 0
 * confirmed this must run before the first `verify()` call — there is no
 * default.
 *
 * Any code path that will sign or verify Ed25519 signatures should import
 * from `@/bindu/identity` BEFORE its first crypto call. The Layer graph in
 * `src/index.ts` ensures that by requiring this barrel before the client
 * layer is constructed.
 */

import "./bootstrap"

export * from "./verify"
export * as Resolve from "./resolve"
