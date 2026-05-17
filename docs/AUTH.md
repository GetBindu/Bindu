# Calling a Bindu agent when auth is on

When `AUTH__ENABLED=true`, every call to a Bindu agent must do **two things**:

1. **Prove you're allowed** — attach a short-lived bearer token from Hydra (the OAuth server).
2. **Prove you're really you** — sign the request body with your DID's private key and attach the signature.

Either one missing → the agent rejects with `-32009`. Get both right → the request goes through.

That's the whole model. The rest of this doc shows you exactly what to put on the wire.

> **Want the long-form explanation?** [AUTHENTICATION.md](./AUTHENTICATION.md) covers the bearer-token half in depth; [DID.md](./DID.md) covers the signing half. This page is the shortest path to a working request.

---

## The four headers, in one picture

Every request to an auth-on Bindu agent carries these four headers:

```
Authorization:    Bearer <access_token>           ← from Hydra, expires in ~1h
X-DID:            did:bindu:<author>:<name>:<id>  ← your identity
X-DID-Timestamp:  <unix-seconds>                  ← within 300s of server clock
X-DID-Signature:  <base58 Ed25519 sig>            ← signs {body, did, timestamp}
```

The agent verifies them in four gates. The first failure stops the chain:

| Gate | What's checked | Failure code |
| --- | --- | --- |
| 1 | Bearer token is active in Hydra | `invalid_token` / `expired` |
| 2 | `X-DID` matches the token's `client_id` | `did_mismatch` |
| 3 | A public key for that DID is registered in Hydra's client metadata | `public_key_unavailable` |
| 4 | Timestamp within 300s **and** signature verifies against the public key | `timestamp_out_of_window` / `crypto_mismatch` |

If all four pass, your handler runs.

---

## I just want it to work — use a built-in caller

Most people shouldn't hand-roll this. Three callers in the repo do the whole chain for you:

| Caller | What you provide | What it does |
| --- | --- | --- |
| **Inbox** (`POST /api/compose`) | Persona + OpenRouter key (via UI) | Spawns your personal agent, registers it with Hydra, signs every outbound message. See [inbox/README.md](../inbox/README.md). |
| **Gateway** (`POST /plan`) | `BINDU_GATEWAY_DID_SEED` + Hydra URLs | Same identity for every peer call. See [GATEWAY.md](./GATEWAY.md). |
| **Postman collection** | Seed + DID + secret in environment | Pre-request script signs each call. See `docs/postman-did-signing.js`. |

If you're testing against an auth-on agent right now, the fastest verification is:

```bash
# In the inbox, with poet_agent running on 5776 with AUTH on:
curl -s -X POST http://127.0.0.1:3787/api/ecosystem \
  -H 'content-type: application/json' \
  -d '{"id":"poet_agent","url":"http://127.0.0.1:5776"}'

curl -s -X POST http://127.0.0.1:3787/api/compose \
  -H 'content-type: application/json' \
  -d '{"agentId":"poet_agent","text":"write a 4-line poem"}'
# → {"ok":true,"status":200,"contextId":"...","taskId":"...","response":{...}}
```

If `ok:true, status:200` comes back, every gate above passed. You're done.

The rest of this doc is for people writing the caller from scratch in a new language.

---

## Hand-rolling it: one-time setup

You need three durable artifacts: a **seed** (your secret), a **DID** (your public name), and an **OAuth client** registered in Hydra that ties them together.

```bash
uv run python -c "
import hashlib, os, base64, base58
from nacl.signing import SigningKey

AUTHOR = 'you_at_example_com'   # your email, @ → _at_, . → _
NAME   = 'my_agent'              # short label, no colons

seed = os.urandom(32)
pk   = bytes(SigningKey(seed).verify_key)
sha  = hashlib.sha256(pk).hexdigest()
agent_id = f'{sha[0:8]}-{sha[8:12]}-{sha[12:16]}-{sha[16:20]}-{sha[20:32]}'
did = f'did:bindu:{AUTHOR}:{NAME}:{agent_id}'

print('SEED_B64       =', base64.b64encode(seed).decode())
print('DID            =', did)
print('PUBLIC_KEY_B58 =', base58.b58encode(pk).decode())
"
```

Save all three. **The seed is your private key — losing it orphans the DID, leaking it lets anyone impersonate you.**

Now register the client in Hydra. The DID *is* the `client_id`:

```bash
CLIENT_SECRET=$(openssl rand -base64 32 | tr -d '=' | tr '+/' '-_')

curl -X POST https://hydra-admin.getbindu.com/admin/clients \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id":     "'"$DID"'",
    "client_secret": "'"$CLIENT_SECRET"'",
    "grant_types":   ["client_credentials"],
    "response_types":["token"],
    "scope":         "openid offline agent:read agent:write",
    "token_endpoint_auth_method": "client_secret_post",
    "metadata": {
      "did":                 "'"$DID"'",
      "public_key":          "'"$PUBLIC_KEY_B58"'",
      "key_type":            "Ed25519",
      "verification_method": "Ed25519VerificationKey2020",
      "hybrid_auth":          true
    }
  }'
```

The critical field is `metadata.public_key` — that's how the agent finds your public key at Gate 3. Save the `client_secret`; you need it to mint tokens.

---

## Hand-rolling it: every request

Four steps. The first one runs ~once an hour (token cache); the other three run every call.

### 1 · Mint a bearer token

```bash
curl -s -X POST https://hydra.getbindu.com/oauth2/token \
  -d grant_type=client_credentials \
  -d "client_id=$DID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "scope=agent:read agent:write"
```

Response:

```json
{ "access_token": "ory_at_...", "expires_in": 3599, "scope": "agent:read agent:write", "token_type": "bearer" }
```

Cache the token in memory; refresh ~60s before `expires_in` runs out.

### 2 · Build the JSON-RPC body

Serialize it **once** and keep the exact bytes. The bytes you sign must equal the bytes you send.

```python
body_bytes = json.dumps({
  "jsonrpc": "2.0",
  "id":      "<uuid>",
  "method":  "message/send",
  "params": {
    "message": {
      "role": "user", "kind": "message",
      "parts": [{"kind": "text", "text": "your prompt"}],
      "messageId": "<uuid>", "contextId": "<uuid>", "taskId": "<uuid>"
    }
  }
}).encode("utf-8")
```

### 3 · Sign

The signing payload is a **second** JSON object that wraps the body as a string:

```python
ts = int(time.time())
signing_str = json.dumps(
    {"body": body_bytes.decode("utf-8"), "did": did, "timestamp": ts},
    sort_keys=True,   # ← required
)
# default Python separators: ", " and ": " — note the spaces.
sig_b58 = base58.b58encode(SigningKey(seed).sign(signing_str.encode("utf-8")).signature).decode()
```

> ⚠️ **The #1 cross-language gotcha.** JavaScript's `JSON.stringify` omits spaces after `:` and `,`; Python's `json.dumps` includes them. The signing payload above uses Python's defaults. If you sign one shape and the server reconstructs the other, signatures mismatch and you'll see `crypto_mismatch`. Use the [canonical fixture](#canonical-fixture) to verify your implementation in any language.

### 4 · Send with all four headers

```python
requests.post(
    f"{agent_url}/",
    data=body_bytes,                          # ← exactly the bytes you signed
    headers={
        "Content-Type":    "application/json",
        "Authorization":   f"Bearer {access_token}",
        "X-DID":           did,
        "X-DID-Timestamp": str(ts),
        "X-DID-Signature": sig_b58,
    },
)
```

If the agent's middleware passes all four gates, your handler runs and you get a normal task response back.

---

## What can go wrong

| Symptom | Most likely cause | Fix |
| --- | --- | --- |
| `-32009 Authentication is required` | No `Authorization` header | Mint a token, attach it |
| `invalid_token` on introspection | Token expired | Mint a fresh one (tokens last ~1h) |
| `did_mismatch` | `X-DID` doesn't match the token's `client_id` | Make sure you minted the token with the same DID you're sending as `X-DID` |
| `public_key_unavailable` | `metadata.public_key` wasn't set when you registered, or you registered against a different Hydra | `GET /admin/clients/<did>` and check |
| `timestamp_out_of_window` | Server and your machine disagree by more than 300s, OR you cached + replayed a signature | Re-sign on every request; check `date -u` |
| `crypto_mismatch` | Body bytes drifted between sign and send, OR sort_keys/whitespace mismatch | Sign the exact bytes you'll send; use the canonical fixture below |
| `invalid_client` at `/oauth2/token` | Wrong `client_secret` or client not registered on this Hydra | Confirm with `GET /admin/clients/<did>` |
| `invalid_scope` at `/oauth2/token` | Asking for a scope you didn't register | Either re-register with the scope or drop it |

A debugging shortcut: introspect your own token and check `client_id` is what you expect.

```bash
curl -s -X POST https://hydra-admin.getbindu.com/admin/oauth2/introspect \
  -d "token=$ACCESS_TOKEN" \
  | python3 -m json.tool
```

Look for `active: true`, `client_id == your DID`, and `exp > now`. If any of these is off, that's your bug.

---

## Canonical fixture

Use this to verify your sign-and-encode implementation matches every other Bindu caller.

| Input | Value |
| --- | --- |
| Seed | 32 zero bytes |
| DID | `did:bindu:test` |
| Body | `{"test": "value"}` |
| Timestamp | `1000` |

Signing payload (note spaces after `:` and `,`):

```
{"body": "{\"test\": \"value\"}", "did": "did:bindu:test", "timestamp": 1000}
```

Expected base58 signature:

```
3SfU4VPTHLbzZzCn17ZqU6y2tnzHQbdo2nnXQr6XZXk34XgyzwSKRrCYEWRmmGXrV39mdkyhTsy5oasfTpNuqyM2
```

Your code matches → ship it. Doesn't match → you're missing the spaces, your keys aren't sorted, or your base58 alphabet is wrong (Bindu uses Bitcoin alphabet — `nacl-base58` uses the same).

---

## Reference

- [AUTHENTICATION.md](./AUTHENTICATION.md) — full teaching-voice walkthrough of the bearer-token side
- [DID.md](./DID.md) — full teaching-voice walkthrough of the signing side
- [`gateway/src/bindu/identity/local.ts`](../gateway/src/bindu/identity/local.ts) — reference TypeScript implementation
- [`inbox/server/index.ts`](../inbox/server/index.ts) §_outbound A2A auth_ + §_DID signature_ — same flow, plain Node
- [`docs/postman-did-signing.js`](./postman-did-signing.js) — Postman pre-request script
