/**
 * Frontend DID signing POC — gives a browser-side user a stable DID so
 * they can call DID-enforced Bindu agents directly from the UI without
 * the gateway acting as a signing proxy.
 *
 * ┌────────────────────────────────────────────────────────────────────┐
 * │  POC ONLY — NOT PRODUCTION.                                        │
 * │                                                                    │
 * │  The Ed25519 seed is persisted in ``localStorage`` under the key   │
 * │  ``bindu:poc:did:seed``. Any script that runs on the same origin   │
 * │  can read it. A single reflected-XSS bug = stolen signing key =    │
 * │  attacker impersonates this user against every DID-enforced agent  │
 * │  they've ever talked to. Do not adopt this for real user identity. │
 * │                                                                    │
 * │  The real path is either:                                          │
 * │    - Web Crypto + IndexedDB with non-extractable keys, or          │
 * │    - Hardware-backed keys via WebAuthn / passkeys, or              │
 * │    - Server-side signing with a session-scoped OAuth identity.     │
 * │  All three are out of scope for this POC; see                      │
 * │  ``docs/GATEWAY_DID_SETUP.md`` for the plan.                       │
 * └────────────────────────────────────────────────────────────────────┘
 *
 * Contract match: produces the same three X-DID-* headers the Python
 * verifier at ``bindu/utils/did/signature.py`` reconstructs. The
 * ``pythonSortedJson`` helper below replicates ``json.dumps(sort_keys=True)``
 * byte-for-byte — default Python separators include SPACES after ``:``
 * and ``,``, which ``JSON.stringify`` omits. That one-character drift
 * flips the signing input and surfaces downstream as ``crypto_mismatch``.
 * The cross-language parity test in ``did.test.ts`` guards against it.
 */

import "./bootstrap"; // MUST be first — wires ed25519.etc.sha512Sync
import * as ed25519 from "@noble/ed25519";
import { sha256 } from "@noble/hashes/sha2.js";
import bs58 from "bs58";

export interface DidSignatureHeaders {
	"X-DID": string;
	"X-DID-Timestamp": string;
	"X-DID-Signature": string;
}

/**
 * Minimal Storage shape the POC needs. ``localStorage`` satisfies it,
 * but tests (and any non-browser environment) can inject a Map-backed
 * stand-in. Keeps the module pure-function at the edge.
 */
export interface DidStorage {
	getItem(key: string): string | null;
	setItem(key: string, value: string): void;
	removeItem(key: string): void;
}

export interface PocIdentity {
	readonly did: string;
	readonly publicKeyBase58: string;
	/** Sign the exact body string. Caller MUST pass the same bytes it
	 *  sends over the wire — any serializer drift breaks the signature. */
	sign(body: string, timestamp?: number): Promise<DidSignatureHeaders>;
}

export interface GetOrCreateOptions {
	/** Embedded in the DID so operator logs can distinguish browsers. */
	author: string;
	/** Embedded in the DID. Typically ``"frontend-poc"``. */
	name: string;
	/** Storage for the seed. Defaults to ``globalThis.localStorage``.
	 *  Tests inject a Map-backed stub. */
	storage?: DidStorage;
	/** Override the storage key. Only for tests — leave default otherwise. */
	storageKey?: string;
}

export const POC_STORAGE_KEY = "bindu:poc:did:seed";

/**
 * Sanitize an author identifier into DID-safe form. Mirrors the gateway
 * + Python sanitizer so a browser using "ops@example.com" produces the
 * same author segment as the gateway does.
 */
export function sanitizeAuthor(raw: string): string {
	return raw.replace(/@/g, "_at_").replace(/\./g, "_");
}

/**
 * Derive a stable 16-byte agent id from the public key, UUID-formatted.
 * Matches Python's ``did_agent_extension`` so the same seed always
 * produces the same DID regardless of which runtime built it.
 */
export function deriveAgentId(publicKey: Uint8Array): string {
	const hash = sha256(publicKey);
	const h = Array.from(hash.slice(0, 16))
		.map((b) => b.toString(16).padStart(2, "0"))
		.join("");
	return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20, 32)}`;
}

/**
 * Match Python's ``json.dumps(obj, sort_keys=True)`` output byte-for-byte.
 *
 * Python's default separators are ``(", ", ": ")`` — WITH spaces after
 * ``:`` and ``,``. ``JSON.stringify`` uses ``(",", ":")`` — no spaces.
 * The one-character difference produces a different signing input, so
 * the verifier reconstructs a different payload and returns
 * ``crypto_mismatch`` even when the caller signed exactly the "right"
 * data. This helper replicates Python's spacing exactly.
 *
 * Also sorts object keys alphabetically at every nesting level — again
 * matching Python's ``sort_keys=True``.
 */
export function pythonSortedJson(value: unknown): string {
	if (value === null) return "null";
	if (typeof value === "boolean") return value ? "true" : "false";
	if (typeof value === "number") {
		if (!Number.isFinite(value)) {
			throw new Error(`Non-finite number not JSON-serializable: ${value}`);
		}
		return String(value);
	}
	if (typeof value === "string") return JSON.stringify(value);
	if (Array.isArray(value)) {
		return "[" + value.map(pythonSortedJson).join(", ") + "]";
	}
	if (typeof value === "object") {
		const obj = value as Record<string, unknown>;
		const keys = Object.keys(obj).sort();
		return (
			"{" +
			keys.map((k) => JSON.stringify(k) + ": " + pythonSortedJson(obj[k])).join(", ") +
			"}"
		);
	}
	throw new Error(`Unsupported type for Python-compat JSON: ${typeof value}`);
}

/**
 * Low-level signer. Reproduces the Python
 * ``sign_request`` + ``create_signature_payload`` pipeline byte-for-byte:
 *
 *   1. Build ``{"body": body, "did": did, "timestamp": ts}``
 *   2. Serialize with Python-compatible ``json.dumps(sort_keys=True)``
 *   3. Ed25519-sign the UTF-8 bytes of the serialized string
 *   4. Base58-encode the signature
 *
 * Exported so the cross-language contract test can drive it with a
 * canonical fixture and assert byte-exact agreement with Python and the
 * gateway signer.
 */
export async function signPayload(params: {
	seed: Uint8Array;
	did: string;
	body: string;
	timestamp: number;
}): Promise<DidSignatureHeaders> {
	const payloadStr = pythonSortedJson({
		body: params.body,
		did: params.did,
		timestamp: params.timestamp,
	});
	const sig = await ed25519.signAsync(new TextEncoder().encode(payloadStr), params.seed);
	return {
		"X-DID": params.did,
		"X-DID-Timestamp": String(params.timestamp),
		"X-DID-Signature": bs58.encode(sig),
	};
}

/**
 * Encode/decode seed bytes to base64 for localStorage.
 *
 * ``btoa`` + ``atob`` are binary-safe on byte-valued strings but can't
 * swallow a raw ``Uint8Array``, hence the String.fromCharCode round-trip.
 */
function encodeSeed(seed: Uint8Array): string {
	let bin = "";
	for (const byte of seed) bin += String.fromCharCode(byte);
	return btoa(bin);
}

function decodeSeed(b64: string): Uint8Array {
	const bin = atob(b64);
	const out = new Uint8Array(bin.length);
	for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
	if (out.length !== 32) {
		throw new Error(
			`Stored DID seed must be 32 bytes (got ${out.length}). ` +
				`The ${POC_STORAGE_KEY} entry is corrupt — clear it to regenerate.`,
		);
	}
	return out;
}

function generateSeed(): Uint8Array {
	const seed = new Uint8Array(32);
	// Works in browsers and in Node ≥19 where ``crypto`` is a global.
	const cryptoObj = (globalThis as unknown as { crypto?: Crypto }).crypto;
	if (!cryptoObj?.getRandomValues) {
		throw new Error(
			"globalThis.crypto.getRandomValues is unavailable — the POC DID needs it to generate a seed.",
		);
	}
	cryptoObj.getRandomValues(seed);
	return seed;
}

function resolveStorage(explicit?: DidStorage): DidStorage {
	if (explicit) return explicit;
	const ls = (globalThis as unknown as { localStorage?: DidStorage }).localStorage;
	if (!ls) {
		throw new Error(
			"localStorage is not available — call getOrCreatePocIdentity() from the browser, " +
				"or pass a custom storage (e.g. during SSR/tests).",
		);
	}
	return ls;
}

/**
 * Get-or-create the browser's POC DID identity.
 *
 * First call on a fresh browser: generates a random 32-byte seed,
 * persists it to ``localStorage[bindu:poc:did:seed]`` (base64), and
 * returns the derived identity.
 *
 * Subsequent calls: reads the seed back and rebuilds the same identity.
 * The DID is therefore stable per-browser until the user clears storage.
 *
 * Throws if ``localStorage`` isn't reachable (SSR, sandboxed iframe,
 * private mode with storage disabled). Callers that need server-side
 * rendering should pass a custom storage or gate this call behind a
 * browser check.
 */
export function getOrCreatePocIdentity(opts: GetOrCreateOptions): PocIdentity {
	const storage = resolveStorage(opts.storage);
	const key = opts.storageKey ?? POC_STORAGE_KEY;

	let seed: Uint8Array;
	const existing = storage.getItem(key);
	if (existing) {
		seed = decodeSeed(existing);
	} else {
		seed = generateSeed();
		storage.setItem(key, encodeSeed(seed));
	}

	const publicKey = ed25519.getPublicKey(seed);
	const publicKeyBase58 = bs58.encode(publicKey);
	const agentId = deriveAgentId(publicKey);
	const did = `did:bindu:${sanitizeAuthor(opts.author)}:${opts.name}:${agentId}`;

	return {
		did,
		publicKeyBase58,
		sign: (body, timestamp) =>
			signPayload({
				seed,
				did,
				body,
				timestamp: timestamp ?? Math.floor(Date.now() / 1000),
			}),
	};
}

/**
 * Delete the stored seed. Useful for "log out"-style POC flows, or to
 * rotate a leaked dev key. Callers that re-invoke ``getOrCreatePocIdentity``
 * afterward will get a brand-new DID.
 */
export function clearPocIdentity(storage?: DidStorage, key: string = POC_STORAGE_KEY): void {
	resolveStorage(storage).removeItem(key);
}
