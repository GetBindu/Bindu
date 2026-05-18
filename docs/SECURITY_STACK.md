# The Security Stack: mTLS + Hydra + DID

## Before you read this

This page assumes you've already read [AUTHENTICATION.md](./AUTHENTICATION.md) and [DID.md](./DID.md). Those two pages explain authentication (the "do you have a ticket?" question) and DIDs (the "are you really you?" question) in isolation.

This page is about **how all three layers work together** on a single request, and what changed on 2026-05-18 when mTLS became the default for the personal agent. If the other two pages are about each musician's instrument, this is the page about the band.

The short version of where each layer fits:

```
Layer 3:  DID signature     →  "is this message tampered with?"     (Ed25519, in the body)
Layer 2:  OAuth2 token      →  "are you allowed to make this call?" (Hydra, in the header)
Layer 1:  mTLS certificate  →  "are you on the wire I think I am?"  (step-ca, at the socket)
```

You need all three because they answer different questions. If you only had OAuth2, an attacker on the wire could read your tokens. If you only had mTLS, anyone with a valid cert could call anything. If you only had DID signatures, you'd know who wrote a message but not whether you should accept it. Together they form a chain — and any one of them can fail safe.

---

## The three questions, one analogy

Imagine you're a courier showing up at a fortified embassy. Before they let you inside, three different officers question you, in this order:

1. **The marine at the front gate** checks that you arrived via the embassy's private armored convoy — not a stranger's truck. _If the convoy isn't ours, you don't even get to the gatehouse._
2. **The receptionist at the desk** asks for your day-pass. The pass was issued this morning, expires at sundown, and lists which rooms you can enter. _If the pass is expired or for the wrong room, you don't get past the desk._
3. **The diplomat in the office** opens the envelope you carried, checks the wax seal, and verifies the seal really was made by the foreign minister who claims to have sent it. _If the seal is missing or fake, your message is rejected even though you got this far._

Three different officers. Three different checks. Three different ways to be rejected. None of them is redundant — each catches a category of attack that the others can't see.

| Embassy | Bindu |
|---|---|
| Armored convoy | **mTLS** — both endpoints present X.509 certs from step-ca; nobody else can speak on this socket |
| Day-pass | **OAuth2 bearer token** — Hydra issued it, ~1h TTL, scoped to specific operations |
| Wax seal | **DID signature** — Ed25519 signature over the JSON body, verifiable with the sender's public key |

---

## What each layer actually does

### Layer 1: mTLS (transport)

**What it answers:** _Is the TCP connection itself private and mutually authenticated?_

When agent A calls agent B over HTTPS, both ends present an X.509 certificate during the TLS handshake. Each cert was issued by Bindu's private step-ca, which only signs certs after the requester proves it owns a Hydra OAuth2 identity. The cert's Subject Alternative Name (SAN) embeds the agent's DID.

Practical consequences:

- A man-in-the-middle can't decrypt traffic, because the session key was negotiated against B's real cert.
- A man-in-the-middle can't impersonate B, because they don't have B's private key.
- A man-in-the-middle can't impersonate A to B either, because B verifies A's client cert too.
- Bearer tokens never traverse the wire in cleartext — they're inside the TLS tunnel.

Cert TTL is **24 hours**. The agent silently renews ~8 hours before expiry. There is no CRL or OCSP — short TTL **is** the revocation strategy.

### Layer 2: Hydra OAuth2 (authorization)

**What it answers:** _Should I let this DID perform this operation right now?_

Each agent registers itself in Hydra as an OAuth2 client. The client_id IS the agent's DID — so the DID lives in three places at once: the cert SAN, the OAuth2 client registry, and the message signature. They have to agree, or the request is rejected.

A caller fetches a bearer token from Hydra (client_credentials grant), then attaches it as `Authorization: Bearer ...` on every HTTP call. The receiver validates the token by introspecting against Hydra. Tokens last ~1h.

Bindu agents currently use a single scope (`agent:read agent:write`); fine-grained authorization is on the roadmap once Kratos lands.

### Layer 3: DID signature (integrity & non-repudiation)

**What it answers:** _Was this exact JSON body authored by the DID it claims, and untampered with since?_

The sender signs the canonical JSON body of the request with their Ed25519 private key. Two HTTP headers carry the proof:

```
X-DID-Identity:   did:bindu:<author>:<name>:<uuid>
X-DID-Signature:  <base58-encoded 64-byte signature>
```

The receiver fetches the sender's public key from the DID document, recomputes the canonical body, and verifies. Even if the bearer token was leaked and the TLS session was somehow compromised, a body that doesn't match the signature gets rejected.

Equally important: **the signature is non-repudiable**. The sender can't later claim "that wasn't me," because no one else has the private key that produced the signature.

---

## What happens on a single request, in order

A poet agent sends a one-line A2A message to a math agent. Both have mTLS on. Here's the full timeline:

```
poet (https://127.0.0.1:5776)                      math (https://127.0.0.1:5775)
    │
    │  TCP SYN, SYN-ACK, ACK
    │ ──────────────────────────────────────────────►│
    │                                                │
    │  TLS ClientHello (presents poet's cert)        │
    │ ──────────────────────────────────────────────►│
    │                                                │
    │  TLS ServerHello (presents math's cert)        │
    │ ◄──────────────────────────────────────────────│
    │                                                │
    │  Both ends verify chain → step-ca root         │
    │  Both ends pin DID in SAN                      │
    │                                                │
    │  [TLS session established — encrypted from here]
    │                                                │
    │  POST /                                        │
    │    Authorization: Bearer ory_at_...            │
    │    X-DID-Identity:  did:bindu:...:poet:...     │
    │    X-DID-Signature: 3xK9...base58              │
    │    Content-Type: application/json              │
    │                                                │
    │    {"jsonrpc":"2.0", "method":"message/send",  │
    │     "params":{"message":{"parts":[...]}}}      │
    │ ──────────────────────────────────────────────►│
    │                                                │
    │                                                │  middleware fires in order:
    │                                                │  1. mTLS already verified cert → DID = poet
    │                                                │  2. Auth middleware introspects Bearer token
    │                                                │     at Hydra → confirms token belongs to poet
    │                                                │  3. DID middleware recomputes signature
    │                                                │     over body → confirms poet authored it
    │                                                │  4. All three identities must match
    │                                                │
    │                                                │  → hand to the handler
```

Any one of those four checks failing rejects the request. The handler never sees an unauthenticated, unverified, or impersonated call.

---

## Today's defaults (as of release 2026.21.1)

Until 2026-05-18, mTLS was opt-in. From 2026.21.1 onward:

| Surface | Default | How to flip |
|---|---|---|
| **Inbox personal agent** | mTLS **on** when `BINDU_PERSONAL_MTLS=1` is set on the comms server | Set the env var before `npm run dev` |
| **Spawned gateway** | mTLS on iff the personal agent has cert files on disk (inherits them) | Automatic — no action |
| **Fleet agents** (`examples/gateway_test_fleet/*.py`) | Plain HTTP unless the full mTLS env block is exported in the launching shell | See the env block below |
| **Custom agents** | Plain HTTP unless `MTLS__ENABLED=true` and Hydra config is provided | Same env block |

The full env block to turn mTLS on for any agent:

```bash
export AUTH__ENABLED=true
export AUTH__PROVIDER=hydra
export HYDRA__ADMIN_URL=https://hydra-admin.getbindu.com
export HYDRA__PUBLIC_URL=https://hydra.getbindu.com
export MTLS__ENABLED=true
export MTLS__MODE=hybrid                    # hybrid keeps Hydra on inbound too
export MTLS__REQUIRE_CLIENT_CERT=false      # set true for full strict-mTLS
export MTLS__CA_URL=https://ca.getbindu.com
export MTLS__CA_ROOT_URL=https://ca.getbindu.com/roots.pem
export BINDU_ALLOW_PRIVATE_WEBHOOK_RANGES=1 # for local 127.0.0.1 webhooks
```

The agent does the rest on its own: registers with Hydra, requests an OIDC token with `aud=step-ca`, exchanges it at step-ca for a 24h X.509 cert, drops the cert files in `<your-agent>/.bindu/`, and serves uvicorn over HTTPS.

---

## Live example: spinning up Leonard and the gateway test fleet

Today's session brought a personal agent (Leonard Hofstadter persona) and the five-agent gateway_test_fleet online, all under real mTLS. Reproduce locally:

### 1. Start the inbox with mTLS on

```bash
cd inbox
BINDU_PERSONAL_MTLS=1 npm run dev
```

Open `http://localhost:3775`, run through the persona wizard, click **Save & Start**. The inbox spawns the personal agent. About 2 seconds later:

- `~/.bindu/personal/.bindu/tls_cert.pem` — real X.509 cert signed by Bindu Intermediate CA, valid 24h, SAN = your DID
- `~/.bindu/personal/.bindu/tls_key.pem` — the agent's private key
- `~/.bindu/personal/.bindu/ca_bundle.pem` — the chain to verify peers

Verify directly:

```bash
$ curl -sk https://127.0.0.1:$(sqlite3 inbox/data/events.db \
    "SELECT substr(url, instr(url, ':' || rowid) + 1)
       FROM personal_agent")/health | jq '.application'
{
  "penguin_id": "53f9d49f-e15b-f38e-bdf6-c7f2c39e6d27",
  "agent_did": "did:bindu:you_at_local:leonard-hofstadter:53f9d49f-e15b-f38e-bdf6-c7f2c39e6d27"
}

$ openssl x509 -in ~/.bindu/personal/.bindu/tls_cert.pem -noout -subject -issuer -ext subjectAltName
subject=CN=did:bindu:you_at_local:leonard-hofstadter:53f9d49f-e15b-f38e-bdf6-c7f2c39e6d27
issuer=CN=Bindu Intermediate CA
X509v3 Subject Alternative Name:
    URI:https://hydra.getbindu.com#did:bindu:you_at_local:leonard-hofstadter:53f9d49f-e15b-f38e-bdf6-c7f2c39e6d27
```

The SAN URI is `https://hydra.getbindu.com#did:bindu:...` — the DID lives in the URL fragment. step-ca's Hydra OIDC provisioner emits it that way.

### 2. Start the fleet

In a separate shell, with the env block exported:

```bash
cd /path/to/Bindu

# Joke
BINDU_PORT=5773 uv run python examples/gateway_test_fleet/joke_agent.py &

# Math
BINDU_PORT=5775 uv run python examples/gateway_test_fleet/math_agent.py &

# Poet
BINDU_PORT=5776 uv run python examples/gateway_test_fleet/poet_agent.py &

# Research
BINDU_PORT=5777 uv run python examples/gateway_test_fleet/research_agent.py &

# FAQ (Bindu docs)
BINDU_PORT=5778 uv run python examples/gateway_test_fleet/faq_agent.py &
```

Each agent boots in ~1.5s on a warm venv. Verify any of them:

```bash
$ curl -sk https://127.0.0.1:5773/health | jq '.application'
{
  "penguin_id": "47191e40-3e91-2ef4-d001-b8d005680279",
  "agent_did": "did:bindu:gateway_test_fleet_at_getbindu_com:joke_agent:47191e40-3e91-2ef4-d001-b8d005680279"
}
```

### 3. Add them to the inbox

In the inbox UI's sidebar, click **+ Add agent**. Paste each URL one at a time:

```
https://127.0.0.1:5773      ← joke_agent
https://127.0.0.1:5775      ← math_agent
https://127.0.0.1:5776      ← poet_agent
https://127.0.0.1:5777      ← research_agent
https://127.0.0.1:5778      ← bindu_docs_agent
```

The inbox fetches each agent's `/.well-known/agent.json` (presenting Leonard's client cert), DID-pins the response against the cert SAN, and stores the agent metadata. From this point, every outbound A2A from Leonard to any fleet agent travels under mTLS.

The sidebar renders each agent as a Gmail-shape address:

```
🌻  joke_agent
    gateway_test_fleet+joke_agent@getbindu.com
🌻  math_agent
    gateway_test_fleet+math_agent@getbindu.com
```

The local part before `+` is the operator, the part after `+` is the agent — exactly Gmail's `+subaddress` convention. Hover any row to see the raw DID.

### 4. Fan-out a multi-agent plan

Compose a message in the inbox that the gateway will fan out across multiple agents (e.g. "write a rap song about bindu's gRPC, get a joke from joke_agent and docs from bindu_docs_agent"). Watch the trace:

```
Plan trace
bindu  · docs_agent_bindu_docs_qa   running… → returned → completed
joke   · agent_tell_joke            running… → returned → completed
poet   · agent_write_poem           running… → returned → completed
```

Every one of those arrows crossed the wire over mTLS. The gateway presented Leonard's cert on each fan-out call; each backing agent verified the chain to Bindu Intermediate CA before processing.

---

## Why this took today to ship — five gotchas, recorded

Default-on mTLS surfaced five real bugs on a developer laptop. They're all fixed in 2026.21.1 and worth knowing if you debug a similar stack from scratch:

1. **`load_dotenv` ordering.** Bindu's `app_settings = Settings()` is constructed at module-import time. If your agent.py imports bindu before calling `load_dotenv`, your MTLS__ env vars land in `os.environ` but never reach the singleton — and the agent silently serves plain HTTP even with `MTLS__ENABLED=true` in the .env file. Always load dotenv first.

2. **Hydra audience drift.** Agents register with Hydra and include `audience: ["step-ca"]` in their client config only when `mtls.enabled` is True at registration time. If your agent registered before mTLS was enabled and you later enable it, the existing-client branch returned early and never patched the audience array. step-ca then rejected token requests with `400: Requested audience 'step-ca' has not been whitelisted`. As of 2026.21.1 the registration flow reconciles drift on every boot.

3. **Reconciliation PUT rotated the secret.** Hydra's `PUT /admin/clients/{id}` is a full replace, and `GET` never returns the client_secret. Building the PUT body from the GET response caused Hydra to overwrite the password with empty — the next `client_credentials` call then returned `401: passwords do not match`. The reconciliation now re-sends the secret from local creds in the PUT body.

4. **Agent card advertised `http://localhost`.** `BinduApplication` defaulted its `url` field to `"http://localhost"` and `bindufy` never passed `deployment.url` through. Peers fetching `/.well-known/agent.json` got an unreachable address (no port, wrong scheme). Fixed by threading the resolved URL into the constructor.

5. **Node 22 undici v6 vs pinned undici v8.** Node's bundled global `fetch` uses undici 6.x; the inbox and gateway both pin undici 8.x for the dispatcher API. Passing a v8 Agent to the v6 global fetch throws an opaque `TypeError: fetch failed`. Both call sites now switch to `undici.fetch` when a dispatcher is in play.

Each one is a one-line idea, and each one would block a green-field deployment. They're all in code now so you shouldn't hit any of them — but if a future stack regression surfaces "fetch failed" or "audience not whitelisted" or silent HTTP fallback, this is the list to walk.

---

## Troubleshooting matrix

| Symptom | Most likely cause | Fix |
|---|---|---|
| Spawn hangs in `starting` for >60s | mTLS env didn't reach `app_settings` (load_dotenv order) OR Hydra audience missing | Check `/health` over both `http://` and `https://` — whichever responds tells you which scheme the agent picked. If HTTP when you expected HTTPS, grep the boot log for `Bootstrapping mTLS` and `Patched Hydra client` |
| `transport: fetch failed` in gateway plan trace | undici v6/v8 mismatch, OR peer's cert SAN doesn't match expected DID | The fix shipped in 2026.21.1; if you're on an older build, upgrade |
| `400 Requested audience 'step-ca' has not been whitelisted` | Hydra client was created before mTLS was enabled | Restart the agent — `register_agent_in_hydra` now patches drift automatically. If still failing, delete `.bindu/oauth_credentials.json` to force a fresh registration |
| `401 passwords do not match` after toggling mTLS | A pre-2026.21.1 reconciliation rotated the client secret | Delete `.bindu/oauth_credentials.json` and restart; the agent will recreate the Hydra client with matching secret |
| Inspector shows `fetch failed` on a healthy agent | `agents` table row points to a stale port from a prior spawn | Re-spawn — 2026.21.1 syncs the row on every spawn. Or `sqlite3 inbox/data/events.db "DELETE FROM agents WHERE id='me'"` and re-add |
| `/.well-known/agent.json` shows `url: "http://localhost"` | Agent built on an older bindu — the URL wasn't threaded into BinduApplication | Upgrade to ≥2026.21.1 |

---

## Operational quick reference

```bash
# What cert is my personal agent serving?
openssl x509 -in ~/.bindu/personal/.bindu/tls_cert.pem -noout -subject -dates -ext subjectAltName

# What audience is my Hydra client configured for?
curl -s "https://hydra-admin.getbindu.com/admin/clients/$(echo -n 'did:bindu:...' | jq -sRr @uri)" | jq '.audience'

# Is the gateway actually using my cert?
ps eww $(pgrep -f gateway.*src/index) | tr ' ' '\n' | grep BINDU_GATEWAY_TLS

# Verify peer DID from a fleet agent's cert SAN
openssl s_client -connect 127.0.0.1:5775 -servername math_agent 2>/dev/null </dev/null \
  | openssl x509 -noout -ext subjectAltName

# Force-renew a cert before TTL (delete + restart)
rm ~/.bindu/personal/.bindu/tls_*.pem ~/.bindu/personal/.bindu/ca_bundle.pem
# then restart the agent
```

---

## Where to read next

- [AUTHENTICATION.md](./AUTHENTICATION.md) — the Hydra side in depth (token lifecycle, scopes, introspection)
- [DID.md](./DID.md) — the DID side in depth (Ed25519, signature canonicalization, key rotation)
- [MTLS_DEPLOYMENT_GUIDE.md](./MTLS_DEPLOYMENT_GUIDE.md) — DevOps-facing guide for deploying step-ca, OIDC provisioner config, cert lifecycle
- [GATEWAY.md](./GATEWAY.md) — how the gateway plans and fan-outs work above this stack
- `release-notes/2026.21.1.txt` — the release that shipped the changes described here
