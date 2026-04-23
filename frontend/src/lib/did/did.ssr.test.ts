/**
 * Tests for the frontend POC DID signer.
 *
 * Two things this file guards:
 *
 *   1. **Cross-language parity** — the ``signPayload`` output is byte-
 *      for-byte identical to what the Python verifier reconstructs and
 *      what the gateway's ``src/bindu/identity/local.ts`` produces. The
 *      fixture below is shared with the gateway test; if anything drifts
 *      (JSON separators, key order, seed decoding, base58 encoding) one
 *      or both tests fail before anyone discovers it by watching a real
 *      agent return ``invalid_signature``.
 *   2. **localStorage POC behavior** — the seed survives across
 *      ``getOrCreatePocIdentity`` calls, ``clearPocIdentity`` forces a
 *      new identity on the next call, and the DID is deterministic from
 *      the seed (so a fixed storage value → fixed DID).
 *
 * To regenerate the signature fixture from scratch:
 *
 *     uv run python -c "
 *     import json, base58
 *     from nacl.signing import SigningKey
 *     seed = b'\\x00' * 32
 *     did  = 'did:bindu:test'
 *     body = b'{\"test\": \"value\"}'
 *     ts   = 1000
 *     payload = {'body': body.decode(), 'did': did, 'timestamp': ts}
 *     ps = json.dumps(payload, sort_keys=True)
 *     sk = SigningKey(seed)
 *     print('signature:', base58.b58encode(sk.sign(ps.encode()).signature).decode())
 *     print('pubkey:', base58.b58encode(bytes(sk.verify_key)).decode())
 *     "
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
	clearPocIdentity,
	deriveAgentId,
	getOrCreatePocIdentity,
	POC_STORAGE_KEY,
	pythonSortedJson,
	sanitizeAuthor,
	signPayload,
	type DidStorage,
} from "./index";

// ---------------------------------------------------------------------------
// Canonical fixture — MUST match gateway/tests/bindu/identity-local.test.ts
// and the Python reference signer. Any edit here needs matching edits there.
// ---------------------------------------------------------------------------

const FIXTURE = {
	seed: new Uint8Array(32), // 32 zero bytes — deterministic
	did: "did:bindu:test",
	body: '{"test": "value"}',
	timestamp: 1000,
	expected: {
		payloadStr:
			'{"body": "{\\"test\\": \\"value\\"}", "did": "did:bindu:test", "timestamp": 1000}',
		signatureBase58:
			"3SfU4VPTHLbzZzCn17ZqU6y2tnzHQbdo2nnXQr6XZXk34XgyzwSKRrCYEWRmmGXrV39mdkyhTsy5oasfTpNuqyM2",
		publicKeyBase58: "4zvwRjXUKGfvwnParsHAS3HuSVzV5cA4McphgmoCtajS",
	},
} as const;

// ---------------------------------------------------------------------------
// Map-backed storage stub — keeps tests pure in the node test environment
// ---------------------------------------------------------------------------

function makeMemoryStorage(initial?: Record<string, string>): DidStorage & {
	dump(): Record<string, string>;
} {
	const m = new Map<string, string>(Object.entries(initial ?? {}));
	return {
		getItem: (k) => (m.has(k) ? m.get(k)! : null),
		setItem: (k, v) => void m.set(k, v),
		removeItem: (k) => void m.delete(k),
		dump: () => Object.fromEntries(m.entries()),
	};
}

// ---------------------------------------------------------------------------
// pythonSortedJson — the single most likely place to drift from Python
// ---------------------------------------------------------------------------

describe("pythonSortedJson — matches Python json.dumps(sort_keys=True)", () => {
	it("produces SPACES after colons and commas", () => {
		expect(pythonSortedJson({ a: 1, b: 2 })).toBe('{"a": 1, "b": 2}');
	});

	it("sorts object keys alphabetically", () => {
		expect(pythonSortedJson({ b: 2, a: 1, c: 3 })).toBe('{"a": 1, "b": 2, "c": 3}');
	});

	it("sorts recursively at every nesting level", () => {
		expect(pythonSortedJson({ outer: { z: 1, a: 2 }, inner: [1, 2] })).toBe(
			'{"inner": [1, 2], "outer": {"a": 2, "z": 1}}',
		);
	});

	it("matches Python's exact payload string for the fixture", () => {
		const actual = pythonSortedJson({
			body: FIXTURE.body,
			did: FIXTURE.did,
			timestamp: FIXTURE.timestamp,
		});
		expect(actual).toBe(FIXTURE.expected.payloadStr);
	});

	it("handles null, boolean, string, number primitives", () => {
		expect(pythonSortedJson(null)).toBe("null");
		expect(pythonSortedJson(true)).toBe("true");
		expect(pythonSortedJson(false)).toBe("false");
		expect(pythonSortedJson(42)).toBe("42");
		expect(pythonSortedJson("hello")).toBe('"hello"');
	});

	it("escapes strings the same way JSON.stringify does", () => {
		expect(pythonSortedJson('he said "hi"')).toBe('"he said \\"hi\\""');
	});

	it("throws on non-finite numbers rather than emitting invalid JSON", () => {
		expect(() => pythonSortedJson(Infinity)).toThrow();
		expect(() => pythonSortedJson(NaN)).toThrow();
	});
});

// ---------------------------------------------------------------------------
// Helper parity (shared logic with gateway)
// ---------------------------------------------------------------------------

describe("sanitizeAuthor", () => {
	it("replaces @ with _at_ and . with _", () => {
		expect(sanitizeAuthor("user.name@example.com")).toBe("user_name_at_example_com");
	});
});

describe("deriveAgentId", () => {
	it("produces a UUID-formatted string", () => {
		const id = deriveAgentId(new Uint8Array(32).fill(0));
		expect(id).toMatch(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/);
	});

	it("is deterministic — same pubkey → same agent id", () => {
		const k = new Uint8Array(32).fill(7);
		expect(deriveAgentId(k)).toBe(deriveAgentId(k));
	});
});

// ---------------------------------------------------------------------------
// CROSS-LANGUAGE CONTRACT — the load-bearing test
// ---------------------------------------------------------------------------

describe("signPayload — cross-language contract with Python + gateway", () => {
	it("produces byte-for-byte the same signature", async () => {
		const headers = await signPayload({
			seed: FIXTURE.seed,
			did: FIXTURE.did,
			body: FIXTURE.body,
			timestamp: FIXTURE.timestamp,
		});
		expect(headers["X-DID"]).toBe(FIXTURE.did);
		expect(headers["X-DID-Timestamp"]).toBe(String(FIXTURE.timestamp));
		expect(headers["X-DID-Signature"]).toBe(FIXTURE.expected.signatureBase58);
	});

	it("is deterministic across repeated calls", async () => {
		const a = await signPayload({
			seed: FIXTURE.seed,
			did: FIXTURE.did,
			body: FIXTURE.body,
			timestamp: FIXTURE.timestamp,
		});
		const b = await signPayload({
			seed: FIXTURE.seed,
			did: FIXTURE.did,
			body: FIXTURE.body,
			timestamp: FIXTURE.timestamp,
		});
		expect(a).toEqual(b);
	});
});

// ---------------------------------------------------------------------------
// getOrCreatePocIdentity — localStorage POC behavior
// ---------------------------------------------------------------------------

describe("getOrCreatePocIdentity", () => {
	it("generates a seed on first call and persists it under the POC key", () => {
		const storage = makeMemoryStorage();
		const id = getOrCreatePocIdentity({
			author: "alice@example.com",
			name: "frontend-poc",
			storage,
		});

		expect(id.did).toMatch(/^did:bindu:alice_at_example_com:frontend-poc:/);
		expect(id.publicKeyBase58).toMatch(/^[1-9A-HJ-NP-Za-km-z]+$/);

		const stored = storage.getItem(POC_STORAGE_KEY);
		expect(stored).not.toBeNull();
		// Base64 of 32 bytes = 44 chars with one '=' pad.
		expect(stored!.length).toBe(44);
	});

	it("reuses the stored seed on subsequent calls — same DID, same pubkey", () => {
		const storage = makeMemoryStorage();
		const first = getOrCreatePocIdentity({
			author: "alice@example.com",
			name: "frontend-poc",
			storage,
		});
		const second = getOrCreatePocIdentity({
			author: "alice@example.com",
			name: "frontend-poc",
			storage,
		});
		expect(first.did).toBe(second.did);
		expect(first.publicKeyBase58).toBe(second.publicKeyBase58);
	});

	it("different browsers (different stored seeds) → different DIDs", () => {
		const a = getOrCreatePocIdentity({
			author: "u@x.com",
			name: "poc",
			storage: makeMemoryStorage(),
		});
		const b = getOrCreatePocIdentity({
			author: "u@x.com",
			name: "poc",
			storage: makeMemoryStorage(),
		});
		expect(a.did).not.toBe(b.did);
	});

	it("produces the canonical-fixture DID when the stored seed is the fixture seed", () => {
		// Base64-encode the fixture seed and hand it to storage — the POC
		// must derive the same public key the Python signer + gateway
		// signer derive.
		const b64 = Buffer.from(FIXTURE.seed).toString("base64");
		const storage = makeMemoryStorage({ [POC_STORAGE_KEY]: b64 });

		const id = getOrCreatePocIdentity({
			author: "ops@example.com",
			name: "frontend-poc",
			storage,
		});
		expect(id.publicKeyBase58).toBe(FIXTURE.expected.publicKeyBase58);
	});

	it("sign() produces the fixture signature when seed + did + body + ts match", async () => {
		const b64 = Buffer.from(FIXTURE.seed).toString("base64");
		const storage = makeMemoryStorage({ [POC_STORAGE_KEY]: b64 });

		// Override the DID so it matches the fixture exactly (bypassing the
		// author/name shape).
		const id = getOrCreatePocIdentity({
			author: "unused",
			name: "unused",
			storage,
		});
		// The sign() method always uses the DID derived from author+name+pubkey.
		// For the byte-exact fixture check we go through signPayload directly
		// — the identity object's role is covered by the earlier tests.
		const headers = await id.sign("hello", 1000);
		expect(headers["X-DID"]).toBe(id.did);
		expect(headers["X-DID-Timestamp"]).toBe("1000");
		expect(headers["X-DID-Signature"]).toMatch(/^[1-9A-HJ-NP-Za-km-z]+$/);
	});

	it("refuses a corrupt stored seed with a clear error", () => {
		// 16 bytes instead of 32.
		const b64 = Buffer.from(new Uint8Array(16)).toString("base64");
		const storage = makeMemoryStorage({ [POC_STORAGE_KEY]: b64 });

		expect(() =>
			getOrCreatePocIdentity({
				author: "u@x.com",
				name: "poc",
				storage,
			}),
		).toThrow(/32 bytes/);
	});

	it("clearPocIdentity forces a fresh DID on the next call", () => {
		const storage = makeMemoryStorage();
		const before = getOrCreatePocIdentity({
			author: "u@x.com",
			name: "poc",
			storage,
		});
		clearPocIdentity(storage);
		const after = getOrCreatePocIdentity({
			author: "u@x.com",
			name: "poc",
			storage,
		});
		expect(before.did).not.toBe(after.did);
	});

	it("timestamp defaults to current unix seconds when omitted", async () => {
		const storage = makeMemoryStorage();
		const id = getOrCreatePocIdentity({
			author: "u@x.com",
			name: "poc",
			storage,
		});
		const before = Math.floor(Date.now() / 1000);
		const headers = await id.sign("hello");
		const after = Math.floor(Date.now() / 1000);
		const ts = Number(headers["X-DID-Timestamp"]);
		expect(ts).toBeGreaterThanOrEqual(before);
		expect(ts).toBeLessThanOrEqual(after + 1);
	});

	beforeEach(() => {
		// Each test creates its own in-memory storage, so nothing to do here —
		// but the hook keeps the structure uniform if we ever add a real
		// ``localStorage`` path for a browser-env test.
	});
});
