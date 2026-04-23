/**
 * Bindu A2A — DID signing pre-request script for Postman.
 *
 * Produces the three X-DID-* headers the Python verifier reconstructs:
 *   X-DID              — your DID string (as-is)
 *   X-DID-Timestamp    — current unix seconds
 *   X-DID-Signature    — base58(Ed25519(json.dumps({"body","did","timestamp"},sort_keys=True)))
 *
 * ────────────────────────────────────────────────────────────────────────
 *  LOAD-BEARING INVARIANT: we sign the exact body bytes Postman sends.
 *  The server verifies by hashing request.body.decode("utf-8"). Any
 *  re-serialization (json.dumps on a parsed object, whitespace
 *  normalization, etc.) flips the bytes and the server returns
 *  reason="crypto_mismatch". Don't touch the body here — we pull the
 *  post-substitution raw string via pm.variables.replaceIn() and sign it
 *  verbatim.
 * ────────────────────────────────────────────────────────────────────────
 *
 * Setup
 * -----
 * 1. Open your Postman collection → Pre-request Script tab on the request
 *    (or collection) that calls a secured Bindu agent. Paste this file.
 *
 * 2. Set two collection or environment variables:
 *
 *      bindu_did       — your DID, e.g. did:bindu:user_at_ex_com:me:<uuid>
 *      bindu_did_seed  — 32-byte Ed25519 seed, base64-encoded
 *
 * 3. Add an `Authorization: Bearer {{bindu_bearer}}` header. Fetch the
 *    bearer token from Hydra once per hour — see the "Hello agent"
 *    section of the Bindu README for the curl command.
 *
 * 4. If your DID doesn't have a seed yet, generate a pair:
 *
 *      uv run python -c "
 *      import os, base64, base58, hashlib
 *      from nacl.signing import SigningKey
 *      seed = os.urandom(32)
 *      sk = SigningKey(seed)
 *      pk = bytes(sk.verify_key)
 *      h = hashlib.sha256(pk).hexdigest()
 *      aid = f'{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'
 *      print('seed :', base64.b64encode(seed).decode())
 *      print('did  : did:bindu:<author>:<name>:' + aid)
 *      "
 *
 * Requires Postman Desktop v11+ (Chromium with Ed25519 in crypto.subtle).
 */

(async () => {
  const did     = pm.variables.get("bindu_did");
  const seedB64 = pm.variables.get("bindu_did_seed");
  if (!did || !seedB64) {
    throw new Error(
      "Set bindu_did and bindu_did_seed variables. See script header for the one-liner to generate them.",
    );
  }

  // 1. The exact body that will hit the wire — post-variable-substitution.
  //    pm.request.body.raw is the TEMPLATE ({{var}} still unresolved);
  //    replaceIn gives us the final string. Signing either one works only
  //    if they're identical; replaceIn is the safe choice.
  const rawTemplate = pm.request.body && pm.request.body.raw ? pm.request.body.raw : "";
  const body = pm.variables.replaceIn(rawTemplate);

  // 2. Timestamp — unix seconds. Server's default skew window is 300s.
  const timestamp = Math.floor(Date.now() / 1000);

  // 3. Build the Python-compat signing payload.
  //    python: json.dumps({"body": body, "did": did, "timestamp": ts}, sort_keys=True)
  //    Default separators have SPACES after ":" and "," — JSON.stringify
  //    omits them. Match exactly or die by crypto_mismatch.
  const payloadStr = pythonSortedJson({ body, did, timestamp });

  // 4. Ed25519-sign via Web Crypto.
  const seed = base64ToBytes(seedB64);
  if (seed.length !== 32) {
    throw new Error(`bindu_did_seed must decode to 32 bytes (got ${seed.length})`);
  }
  const signature = await ed25519Sign(seed, new TextEncoder().encode(payloadStr));

  // 5. Headers — pm.request.headers.upsert replaces any stale values from
  //    a prior run so repeated sends stay consistent.
  pm.request.headers.upsert({ key: "X-DID",           value: did });
  pm.request.headers.upsert({ key: "X-DID-Timestamp", value: String(timestamp) });
  pm.request.headers.upsert({ key: "X-DID-Signature", value: base58Encode(signature) });

  // Uncomment to debug (Postman console: ⌥⌘C):
  // console.log("[bindu] signing payload:", payloadStr);
  // console.log("[bindu] sig:", base58Encode(signature));
})().catch((e) => {
  // Surface errors clearly — Postman swallows thrown promises quietly otherwise.
  console.error("[bindu] pre-request signing failed:", e);
  throw e;
});

// ────────────────────────── helpers ──────────────────────────

function pythonSortedJson(value) {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("non-finite number not JSON-serializable");
    return String(value);
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return "[" + value.map(pythonSortedJson).join(", ") + "]";
  }
  if (typeof value === "object") {
    const keys = Object.keys(value).sort();
    return "{" + keys.map(k => JSON.stringify(k) + ": " + pythonSortedJson(value[k])).join(", ") + "}";
  }
  throw new Error("unsupported type for python-compat JSON: " + typeof value);
}

function base64ToBytes(b64) {
  const bin = atob(b64.replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function ed25519Sign(seed, message) {
  // Web Crypto's importKey("pkcs8") wants the seed wrapped in a 16-byte
  // ASN.1 Ed25519 PKCS8 prefix:
  //   SEQUENCE(46) INTEGER(0) SEQUENCE(5) OID(1.3.101.112) OCTET STRING(34 → 32)
  const PKCS8_PREFIX = new Uint8Array([
    0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06,
    0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20,
  ]);
  const pkcs8 = new Uint8Array(PKCS8_PREFIX.length + seed.length);
  pkcs8.set(PKCS8_PREFIX, 0);
  pkcs8.set(seed, PKCS8_PREFIX.length);

  const key = await crypto.subtle.importKey(
    "pkcs8",
    pkcs8,
    { name: "Ed25519" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign({ name: "Ed25519" }, key, message);
  return new Uint8Array(sig);
}

function base58Encode(bytes) {
  const ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"; // pragma: allowlist secret
  if (bytes.length === 0) return "";

  // Leading zero bytes map to leading "1"s by base58 convention.
  let zeros = 0;
  while (zeros < bytes.length && bytes[zeros] === 0) zeros++;

  let num = 0n;
  for (const b of bytes) num = num * 256n + BigInt(b);

  let s = "";
  while (num > 0n) {
    const r = Number(num % 58n);
    num /= 58n;
    s = ALPHABET[r] + s;
  }
  return "1".repeat(zeros) + s;
}
