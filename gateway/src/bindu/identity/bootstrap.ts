import * as ed25519 from "@noble/ed25519"
import { sha512 } from "@noble/hashes/sha2.js"

/**
 * One-time bootstrap: wire sha512 into @noble/ed25519 v2.
 *
 * Without this, `ed25519.verify` / `verifyAsync` throw
 * `"hashes.sha512Sync not set"` (Phase 0 finding). The package author made
 * this explicit to keep the default bundle small — callers must opt into
 * their hash implementation.
 *
 * Kept as its own file (not inlined in index.ts) so that bundlers can
 * tree-shake the etc object without losing the hook. Side-effectful import
 * order matters; index.ts re-imports this first.
 */

if (!ed25519.etc.sha512Sync) {
  // `sha512(...msgs)` requires a single Uint8Array, so we concat first.
  ed25519.etc.sha512Sync = (...msgs: Uint8Array[]): Uint8Array =>
    sha512(ed25519.etc.concatBytes(...msgs))

  ed25519.etc.sha512Async = async (...msgs: Uint8Array[]): Promise<Uint8Array> =>
    sha512(ed25519.etc.concatBytes(...msgs))
}
