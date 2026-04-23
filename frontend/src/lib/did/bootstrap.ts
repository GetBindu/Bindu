import { hashes } from "@noble/ed25519";
import { sha512 } from "@noble/hashes/sha2.js";

/**
 * One-time bootstrap: wire sha512 into @noble/ed25519 v3.
 *
 * Without this, ``ed25519.sign`` / ``signAsync`` / ``verify`` throw
 * because v3 ships without a bundled hash — callers must opt in. The
 * v3 API exposes this as ``hashes.sha512`` (single-arg) rather than
 * v2's ``etc.sha512Sync`` (rest-args); the frontend uses v3 while the
 * gateway still uses v2, so the two bootstraps look different but wire
 * up the same underlying ``@noble/hashes`` implementation.
 *
 * Side-effectful import — the POC module re-imports this first.
 */
// Cast to ``typeof hashes.sha512`` — the published v3 type is a branded
// ``Bytes & Uint8Array<ArrayBuffer>`` that @noble/hashes' plain Uint8Array
// return can't satisfy structurally. The runtime value is identical.
if (!hashes.sha512) {
	hashes.sha512 = ((message: Uint8Array): Uint8Array =>
		sha512(message)) as unknown as typeof hashes.sha512;
}
hashes.sha512Async = (async (message: Uint8Array): Promise<Uint8Array> =>
	sha512(message)) as unknown as typeof hashes.sha512Async;
