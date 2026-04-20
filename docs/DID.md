# Decentralized Identifiers (DIDs)

## Before you read this

This page assumes you've already read [AUTHENTICATION.md](./AUTHENTICATION.md). If you haven't, go there first. The short version:

- Authentication (bearer tokens, Hydra) answers _"are you allowed to make this request?"_
- DIDs answer the other half: _"are you really who you say you are?"_

You need both. If either is missing, your request is either rejected or — worse — accepted when it shouldn't be. This page explains the second half, carefully, without assuming prior knowledge of cryptography.

---

## The problem DIDs solve

Imagine you run a coffee shop, and every morning a truck pulls up claiming to be your milk delivery. The driver says, _"I'm from Acme Dairy, same as always."_

How do you know they really are? A few options:

1. **Ask for a company ID card.** But anyone can print a card that says "Acme Dairy."
2. **Call Acme and ask, "is this driver yours?"** Works, but requires calling Acme every single morning. Slow. And if Acme's phone is down, you can't accept milk.
3. **Acme issues the driver a _cryptographic_ credential — a physical key that only fits one lock, the lock being one you can verify on the spot.** Each morning the driver proves they have the key. You don't need to call anyone. Even if Acme's office burns down, the key still works.

Option 3 is the spirit of a **DID**. Instead of calling a central authority to vouch for an identity (option 2), the identity holder carries _proof_ they can demonstrate anywhere, to anyone, without a phone call.

For software agents, "calling a central authority" looks like "asking Facebook if this user is real" or "asking a platform if this agent is legitimate." That makes the platform a single point of failure. If the platform disappears, or decides to remove you, your identity disappears too.

DIDs remove the central authority. Your identity lives in math, not in a company's database.

---

## The passport and the badge — an analogy that will carry us through

Pretend you're entering a secured building. The security desk wants to know three things:

1. **Is your face on a real passport?** (Is the document authentic — not forged?)
2. **Does the name on the passport match the face?** (Are you really the person it identifies?)
3. **Do you have a day-pass letting you into this specific building?** (Are you allowed in today?)

Real life uses:

- The **passport** — an expensive-to-forge document, issued once, lasts years. Proves _who you are_.
- The **day-pass** — a sticker you get at the front desk. Proves _you have access today_.

You need both. A passport without a day-pass gets you nowhere (you're a verified stranger). A day-pass without a passport is useless (anyone could claim the sticker).

Bindu uses the exact same pattern:

| Real life | Bindu |
|---|---|
| Passport | **DID + signature** — long-lived cryptographic identity |
| Day-pass | **Bearer token** — short-lived (~1 hour) access grant |
| Photo on passport | **Public key** stored in the DID document |
| Secret signature only you can make | **Private key** that only you hold |
| Security guard checks passport photo | Server checks DID signature |
| Security guard checks day-pass | Server checks bearer token (via Hydra) |

This document is about the passport side. The badge side was [AUTHENTICATION.md](./AUTHENTICATION.md).

---

## Public and private keys, explained without math

Before we get into DID mechanics, we need one concept: **public-key cryptography**. You've probably heard the term. Here's what it actually means, stripped of math.

A **key pair** is two matched pieces of data — a **private key** and a **public key**. They're generated together, once. They have two magical properties:

1. **You can give the public key to anyone.** You should. That's why it's called public.
2. **If you "sign" a message using the private key, anyone with the public key can check the signature.** They can't fake a signature, because they don't have the private key. But they can verify yours.

A useful way to picture it: a private key is like the **one-of-a-kind stamp** a medieval kingdom's scribe uses to seal letters. The stamp is kept in the scribe's locked chest. The king gives an imprint of the stamp (the public key) to every city, so they can check whether a letter really came from the scribe.

A letter without the stamp is just paper. A forgery (someone trying to fake the stamp) gets spotted instantly because the stamp has unique geometry that's impossible to reproduce without the original.

In Bindu we use a specific kind of key pair called **Ed25519**. You don't need to know why Ed25519 specifically — just three facts:

- Keys are tiny (32 bytes each). Cheap to store and send.
- Signing and verifying are fast.
- Ed25519 has been audited to death. Signal uses it. Tor uses it. SSH uses it. It's trustworthy.

Two things we'll come back to:

- **Seed** — a 32-byte random number that _generates_ the key pair. If you have the seed, you can always re-derive both keys. In Bindu, the seed is what you save and protect. Everything else is derived.
- **Signature** — the output of signing a message. 64 bytes, usually encoded as Base58 so it's readable. If a signature verifies against the public key, you're certain it was made by someone holding the private key. If it doesn't, someone tampered with the message or you're looking at a forgery.

---

## What a DID actually is

A DID is just a **string**. A specific shape of string that says, "this identifier belongs to a specific identity system, and here's where to look up more information about it."

Bindu DIDs look like this:

```
did:bindu:dutta_raahul_at_gmail_com:postman:ee67868d-d4b6-6441-93d6-ba4b29dc5e1d
```

Break it into five parts separated by colons:

| Part | Value in our example | What it means |
|---|---|---|
| 1 | `did` | The literal prefix. Says "this is a Decentralized Identifier." Every DID ever, in any system, starts with this. W3C standard. |
| 2 | `bindu` | The **method**. Tells you which DID system to use for resolving this identifier. Others exist: `did:web`, `did:ethr`, `did:key`. Here we use Bindu's method. |
| 3 | `dutta_raahul_at_gmail_com` | The **author segment**. A human-readable identifier of who created this DID. We sanitize emails: `@` becomes `_at_`, `.` becomes `_`. Pure metadata — helps humans know whose agent this is. |
| 4 | `postman` | The **agent name**. A short label you give each agent you run. |
| 5 | `ee67868d-...-ba4b29dc5e1d` | The **agent ID** — a UUID derived from the first 16 bytes of `sha256(public_key)`. This is what makes the DID _unique_. |

The last segment is where the math enters. It's not a random UUID — it's computed from the public key. That has a lovely property: if you change your key, your DID changes too. You can't swap keys while keeping the same DID, because the DID string itself is bound to the key.

### Rules for DID strings

A few constraints worth knowing, from the W3C spec:

- Only ASCII letters, digits, and `._:%-`
- Case-sensitive (`did:bindu:Agent` and `did:bindu:agent` are different identities)
- No `?`, no `#`, no spaces
- Under 2048 characters

And a Bindu-specific one: each of the five segments is always present. If any is missing or empty, the DID is malformed.

---

## The DID document — what the server needs to trust you

The DID _string_ is just a name. To trust someone, the server needs to know their **public key**. That mapping lives in a JSON file called the **DID document**.

Here's a real one:

```json
{
  "@context": [
    "https://www.w3.org/ns/did/v1",
    "https://getbindu.com/ns/v1"
  ],
  "id": "did:bindu:dutta_raahul_at_gmail_com:postman:ee67868d-d4b6-6441-93d6-ba4b29dc5e1d",
  "created": "2026-04-19T17:23:45+00:00",
  "authentication": [
    {
      "id":              "did:bindu:...#key-1",
      "type":            "Ed25519VerificationKey2020",
      "controller":      "did:bindu:...",
      "publicKeyBase58": "BJx2RYuVCGNkgXuxcQEYe8FKTBqypJjz5gvTxXto9kQv"
    }
  ]
}
```

Field by field:

- `@context` — a pointer to the standards this document follows. Don't worry about it; it just tells parsers how to interpret the other fields.
- `id` — the DID itself. Always matches the DID you resolved.
- `created` — timestamp of first publication. Useful for audit and "how old is this agent."
- `authentication` — the heart of the document. Contains one or more **verification methods** — public keys the DID owner has published.

In the verification method:

- `type: Ed25519VerificationKey2020` — "this is an Ed25519 public key, published using the 2020 version of the spec."
- `controller` — who is allowed to update this document. Usually the DID itself (self-controlled).
- `publicKeyBase58` — the actual public key, encoded so it's a short readable string (no padding, no confusing characters like `0/O`).

> **Where is this document stored?** In Bindu, the DID document lives inside the Hydra OAuth client's `metadata` field. When you register a client with Hydra, you put the public key there. The agent fetches the DID document from Hydra when it needs to verify a signature.
>
> There's also a public resolver endpoint (`POST /did/resolve`) that returns the document without needing Hydra admin access. This is the A2A standard path for resolving any DID.

---

## Signing a request — what the client does

Let's say you're the client. You're about to send a JSON-RPC request to an agent. You want to sign it so the agent knows the request really came from you (not someone replaying an old request, not a man-in-the-middle tampering in transit).

Here's what your code has to do, step by step. This is word-for-word what our gateway and our Postman pre-script do.

### Step 1. Gather the three inputs

- **Body** — the exact bytes of the HTTP request body, as they'll hit the wire. Not a parsed object. Not a "reformatted" version. The exact UTF-8 bytes the server will receive. This is the most common thing people get wrong.
- **DID** — your DID string.
- **Timestamp** — current Unix time in seconds (an integer).

### Step 2. Build the signing payload

Combine the three into a small JSON object:

```python
{"body": <body>, "did": <did>, "timestamp": <ts>}
```

Then serialize it **using Python's `json.dumps(sort_keys=True)` convention**. Two things matter:

1. **Keys sorted alphabetically**, at every nesting level. So `body` before `did` before `timestamp`.
2. **Default Python separators** — `", "` and `": "` — with a **space** after the comma and colon.

The second rule is where every other language trips up. JavaScript's `JSON.stringify` omits the spaces by default. Python includes them. If your client leaves out the spaces, the bytes you sign don't match the bytes the server reconstructs, and the signature fails — even though logically you "signed the right data."

A working payload for a small example:

```
{"body": "{\"test\": \"value\"}", "did": "did:bindu:test", "timestamp": 1000}
```

Notice the spaces after `:` and `,`. Notice `body` comes first alphabetically. If your implementation matches Python's `json.dumps(payload, sort_keys=True)`, you're good. The gateway has a helper called `pythonSortedJson` that produces exactly this output.

### Step 3. Sign the bytes

Take the UTF-8 bytes of that payload string, and sign them with your Ed25519 private key. Base58-encode the 64-byte signature.

### Step 4. Attach three headers to the HTTP request

```
X-DID:             <your DID string>
X-DID-Timestamp:   <ts>
X-DID-Signature:   <base58-encoded signature>
```

Plus your bearer token from the authentication flow:

```
Authorization:     Bearer <access token>
```

Send the request. The body on the wire must be _exactly the same bytes_ you put in the signing payload. If there's a middleware that reformats JSON between your sign-step and the network, you'll get a verification failure on the server.

---

## Verifying a request — what the server does

When the agent receives your request, four gates fire in order. If any one fails, the request is rejected and the server tells you which gate failed via a `reason` code. Knowing the gates makes debugging quick.

```
Incoming request
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Gate 1: Bearer token must be valid                           │
│                                                              │
│ Server → Hydra admin: "is this token active?"                │
│ Hydra  → Server:      active=true, client_id=did:bindu:...   │
│                                                              │
│ Fail reasons: invalid_token, expired, unknown                │
└──────────────────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Gate 2: X-DID must match the token's client_id               │
│                                                              │
│ If the bearer token was issued to `did:bindu:A` but the      │
│ X-DID header says `did:bindu:B`, something is off. The       │
│ token's owner disagrees with the claimed identity. Reject.   │
│                                                              │
│ Fail reason: did_mismatch                                    │
└──────────────────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Gate 3: The DID's public key must be known                   │
│                                                              │
│ The server looks up the public key in Hydra's metadata       │
│ (or via the DID resolver). If no public key is registered,   │
│ the signature can't be checked.                              │
│                                                              │
│ Fail reason: public_key_unavailable                          │
└──────────────────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│ Gate 4: Timestamp and signature must both verify             │
│                                                              │
│ 1. Is X-DID-Timestamp within 300 seconds of the server's     │
│    clock? If not → timestamp_out_of_window. This prevents    │
│    old requests from being replayed hours later.             │
│                                                              │
│ 2. Reconstruct the signing payload from the exact body       │
│    bytes + the X-DID + the X-DID-Timestamp. Verify the       │
│    X-DID-Signature against it using the public key from      │
│    Gate 3. If not → crypto_mismatch.                         │
└──────────────────────────────────────────────────────────────┘
      │
      ▼
Request proceeds to handler
```

Each `reason` code in a rejection response points to exactly one gate. That makes debugging narrow:

| Reason | Gate | What's wrong |
|---|---|---|
| `missing_signature_headers` | 2 | You sent a bearer token but no X-DID-* headers |
| `did_mismatch` | 2 | X-DID header disagrees with the token's `client_id` |
| `public_key_unavailable` | 3 | Hydra has no public key registered for this DID |
| `timestamp_out_of_window` | 4 | Clock skew > 300s, or replayed old request |
| `crypto_mismatch` | 4 | Signature doesn't verify — wrong key, wrong bytes, or tampering |

---

## Setting up your own DID from scratch

Let's walk through registering a brand-new identity, end to end. This mirrors what our internal debugging session does every time someone sets up Postman against Bindu.

### 1. Generate a seed and derive everything from it

Run this Python one-liner:

```bash
python3 -c "
import os, base64, base58, hashlib
from nacl.signing import SigningKey

AUTHOR = 'your.email@example.com'   # replace
NAME   = 'my_agent'                  # replace (short, no colons)

seed = os.urandom(32)
sk   = SigningKey(seed)
pk   = bytes(sk.verify_key)
h    = hashlib.sha256(pk).hexdigest()
agent_id = f'{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'
author_safe = AUTHOR.replace('@', '_at_').replace('.', '_')
did  = f'did:bindu:{author_safe}:{NAME}:{agent_id}'

print()
print('did              =', did)
print('seed (base64)    =', base64.b64encode(seed).decode())
print('public key (b58) =', base58.b58encode(pk).decode())
"
```

It outputs three lines. Save them somewhere safe. **The seed is your private key.** If you lose it, this DID is orphaned. If it leaks, the holder can impersonate you.

### 2. Register the client with Hydra

```bash
curl -X POST 'https://hydra-admin.getbindu.com/admin/clients' \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id":     "<the did from step 1>",
    "client_secret": "<a strong random secret — see AUTHENTICATION.md>",
    "grant_types":   ["client_credentials"],
    "response_types": ["token"],
    "scope":         "openid offline agent:read agent:write",
    "token_endpoint_auth_method": "client_secret_post",
    "metadata": {
      "agent_id":            "<the uuid portion of the did>",
      "did":                 "<the did>",
      "public_key":          "<the base58 public key>",
      "key_type":            "Ed25519",
      "verification_method": "Ed25519VerificationKey2020",
      "hybrid_auth":          true
    }
  }'
```

The important field is `metadata.public_key` — that's the base58 public key from step 1. The server uses this at Gate 3 to verify your signatures. The `metadata.did` and `hybrid_auth: true` signal to Bindu that this client requires DID signatures on top of the bearer token.

### 3. Get a bearer token

See [AUTHENTICATION.md](./AUTHENTICATION.md#step-2--exchange-the-secret-for-a-token).

### 4. Sign and send a request

Use the gateway's sign-request helper (`gateway/src/bindu/identity/local.ts`), the frontend POC (`frontend/src/lib/did/`), or a Postman pre-request script (a full example lives in our Postman collection). All three produce identical bytes — they've been cross-tested.

If you're hand-rolling signing in a new language, the rules are in the "Signing a request" section above. Test against the canonical fixture: seed `= 32 zero bytes`, DID `= did:bindu:test`, body `= {"test": "value"}`, timestamp `= 1000`. Your signature should Base58-encode to:

```
3SfU4VPTHLbzZzCn17ZqU6y2tnzHQbdo2nnXQr6XZXk34XgyzwSKRrCYEWRmmGXrV39mdkyhTsy5oasfTpNuqyM2
```

If it doesn't, your Python-compat JSON is almost certainly wrong (missing spaces between keys, or unsorted keys).

---

## What goes wrong — real failure modes

This section is long because this is where people lose hours. Each of these happened to at least one person setting up Bindu. Save yourself the same hours.

### "I'm getting `did_mismatch` and the strings look identical"

The X-DID header on your request must be byte-identical to the `client_id` returned by Hydra when introspecting your bearer token. Three things to check, in this order:

1. **Are you talking to the right Hydra?** If your agent's `HYDRA__ADMIN_URL` points at a different Hydra instance than the one that issued your token, introspection will either fail or return someone else's `client_id`. Run:
   ```bash
   curl -X POST '<your agent hydra admin>/admin/oauth2/introspect' -d 'token=<your token>'
   ```
   The `client_id` field must exactly match `X-DID`.
2. **Did a variable get auto-edited?** Some clients (copy-paste from Slack, from Markdown tables) turn `-` into `–` (en dash). Look for invisible differences with `diff <(xxd <<< "$a") <(xxd <<< "$b")`.
3. **Did Postman or your client keep the old value?** Re-sending with a stale `Authorization` header is common. Open Postman Console (⌥⌘C) and read the actual outgoing headers.

### "I'm getting `crypto_mismatch`"

This means Gate 4 tried to verify your signature and it didn't match. Four causes:

- **Body bytes drifted.** Your signing code serialized a JSON object, then a middleware or HTTP client re-serialized the body before sending. The two serializations look the same but have different whitespace or key order. Fix by signing the exact string you'll put on the wire, not the parsed object.
- **Wrong public key in Hydra.** You rotated your seed locally but forgot to update `metadata.public_key`. The server is verifying against the old public key. Fix by re-registering with the new key.
- **Python-compat JSON mismatch.** JavaScript's `JSON.stringify` omits spaces after `:` and `,`. Python's default includes them. If you signed one and the server reconstructed the other, mismatch. Use `pythonSortedJson` from the gateway, or replicate its behavior.
- **Actually a forged signature / wrong seed.** The seed you signed with doesn't match the public key in Hydra. Check `seed → pubkey → metadata` hasn't drifted.

### "I'm getting `timestamp_out_of_window`"

Two causes:

- **Your clock is wrong.** Check `date -u` against a known-good time server. Container clocks drift.
- **Someone is replaying a captured request.** If you (or your logs) kept a request from 10 minutes ago and tried to resend it, the timestamp is stale. Sign fresh every time.

### "I'm getting `public_key_unavailable`"

The DID in `X-DID` doesn't have a public key registered with Hydra. Two paths:

- You haven't registered yet — do step 2 of "Setting up your own DID" above.
- You registered but put the public key somewhere other than `metadata.public_key`. Look at the response from `GET /admin/clients/<did>` and confirm `metadata.public_key` is a non-empty base58 string.

### "I'm getting `missing_signature_headers`"

You sent `Authorization: Bearer <token>` where the token's `client_id` is a DID, but you forgot to also send the three X-DID-* headers. Once the token's client is a DID, signing becomes mandatory — there's no "unsigned is fine" fallback. The gateway and frontend helpers always set all three.

---

## Keeping your seed safe

The seed is the single thing that gives you authority over your DID. Treat it like a password, minus the recoverability (there's no "forgot seed" flow — once it's gone, the DID is gone).

### Storage

- **Secret manager** (1Password, AWS Secrets Manager, HashiCorp Vault) for individual developers and production.
- **Environment variables loaded from `.env`** for local development, where `.env` is gitignored.
- **Never** in source code. Never committed. Never in plaintext in logs.

### Permissions

On disk, the seed file should be readable only by the user running the agent: `chmod 600`. If you're on Linux/macOS, check:

```bash
ls -l ~/.bindu/oauth_credentials.json
# should show -rw------- (600)
```

### Rotation

Rotating keys regularly is good hygiene. The simplest rotation:

1. Generate a new seed (the same one-liner from setup).
2. Update Hydra with the new public key:
   ```bash
   curl -X PUT 'https://hydra-admin.getbindu.com/admin/clients/<your did>' \
     -H 'Content-Type: application/json' \
     -d '<full client record with updated metadata.public_key>'
   ```
3. Start your agent with the new seed.
4. Discard the old seed.

During the rotation window, old signatures will fail verification. Do it during a maintenance window, or orchestrate a dual-signature period (beyond this document's scope).

### If you suspect compromise

Assume the attacker has full signing authority until you've:

- Rotated the seed (above).
- Invalidated all outstanding bearer tokens (Hydra's admin API can revoke).
- Audited recent requests signed by this DID to see what the attacker might have done.
- Read your logs for unfamiliar `X-DID-Timestamp` values or request patterns.

Don't just rotate — investigate. The seed didn't leak on its own.

---

## Bonus: signed responses from agents

So far we've talked about you signing requests to agents. Agents also sign their responses — every artifact a Bindu agent produces is signed with the agent's seed. That way, when your client sees a task result, you can verify the result really came from the agent and wasn't tampered with in flight.

Look for this field in a task response:

```json
"metadata": {
  "did.message.signature": "<base58 signature>"
}
```

To verify, resolve the agent's DID document, pull the `publicKeyBase58`, and verify the signature against the message bytes. The agent's DID itself is in its agent card at `/.well-known/agent.json`.

You don't _have to_ verify — the server does the heavy lifting at ingest. But if you're building something compliance-heavy (legal, medical, financial), the client-side verification gives you a proof you can put in an audit log.

---

## Signing is not encryption

One clarification that comes up often:

- **Signing** gives you authenticity ("really from this DID") and integrity ("not modified in transit"). It does **not** hide the contents. Anyone who sees the request on the wire can read the body as plaintext JSON.
- **Encryption** hides the contents. For network transport, use HTTPS (TLS). In Bindu, the public Hydra and agent endpoints are HTTPS in production.

If you need messages to be unreadable even by gateways/proxies in the middle, that's **end-to-end encryption** — a separate feature, not part of the DID system. Bindu doesn't currently ship E2E message encryption; TLS + DID signing is the production model.

---

## Why Bindu chose Ed25519 specifically

This is optional reading. The short version: Ed25519 is a modern elliptic-curve signature scheme that's:

- **Small.** Keys are 32 bytes, signatures are 64 bytes. Fits in headers.
- **Fast.** Sub-millisecond signing and verifying on modern CPUs.
- **Deterministic.** The same input always produces the same signature. Makes testing easy (we can check exact fixture signatures across languages).
- **Well-vetted.** Used in Signal, Tor, SSH, most modern crypto. Published in RFC 8032. No known practical attacks.

The alternative was RSA. RSA keys are ten times larger, signatures are larger, signing is slower, and RSA has a long history of subtly broken implementations. For a protocol that signs on every request, Ed25519 is the right default.

If you ever see a DID from outside Bindu using a different key type, the `authentication.type` field in the DID document tells you which algorithm to use. Bindu-native DIDs always use `Ed25519VerificationKey2020`.

---

## References and further reading

Standards:

- [W3C DID Core Specification](https://www.w3.org/TR/did-core/) — the governing standard for DIDs
- [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032) — Ed25519 signature scheme
- [did:bindu method spec](https://getbindu.com/ns/v1) — Bindu-specific DID method

Related Bindu docs:

- [AUTHENTICATION.md](./AUTHENTICATION.md) — the bearer-token side
- [PAYMENT.md](./PAYMENT.md) — the x402 payment protocol, which also uses DIDs
- `docs/GATEWAY_DID_SETUP.md` — operator guide for configuring the gateway's own DID (separate doc, in progress)

Inspiration:

- [Atproto DID spec](https://atproto.com/specs/did) — Bluesky's approach to DIDs, which shares many design decisions

---

## Summary in one paragraph

A DID is a long identifier string that maps, through a public document, to a cryptographic public key. When you make a request, you sign specific bytes with your private key (Ed25519) and attach the signature as an HTTP header. The server resolves your DID to get the public key, reconstructs the same bytes, and verifies. If it matches, it knows the request really came from you and hasn't been modified. Combined with a bearer token from [AUTHENTICATION.md](./AUTHENTICATION.md), this gives Bindu two independent guarantees: _this request is permitted_ (token) and _this request is authentic_ (signature). Lose either and the request is rejected. Get both right and you have a system where identity and access are verifiable end-to-end, without trusting any single central authority.
