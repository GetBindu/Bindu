# Authentication

## Why this page exists

When an agent receives an HTTP request, it has to decide one thing before doing anything else:

> _Should I actually answer this?_

This sounds trivial, but it hides a deep question. A stranger knocks on your door holding an envelope. Before you let them in, you want two things:

1. **Who are they?** — the name on the envelope might be real or might be fake.
2. **Are they allowed in?** — even if the name is real, do they have permission to enter this particular room?

Most "authentication" tutorials mash these together. In Bindu we keep them separate because they need separate tools:

| Question | What answers it | Where it lives |
|---|---|---|
| _Are you allowed to make this request?_ | **Authentication (this page)** — an access token issued by a trusted service | OAuth 2.0 / Ory Hydra |
| _Is this request really from who it claims to be?_ | **DID signing** — a cryptographic signature you can only make with a secret key | See [DID.md](./DID.md) |

You almost always need both. This page is about the first one. Read this, then the DID page. Together they explain the full lifecycle of a real Bindu request.

---

## The idea behind bearer tokens

Imagine a movie theatre. When you buy a ticket, the person at the door doesn't care what your name is — they just want proof that you paid. You hand over a paper ticket, they tear off a stub, and you walk in. The ticket is the _proof_. Anyone holding a valid ticket can get in — that's why it's called a **bearer** token. Whoever bears it (holds it) gets access.

A **bearer token** in HTTP works the same way. It's a random-looking string of characters. Your client attaches it to every request. The server looks at the string and decides "yes, this is a valid ticket — proceed." It doesn't interrogate you further.

A real bearer token in Bindu looks like this:

```
ory_at_hV2cm_iq55iipi8M53mwvQbpNwQNfTTxvJnDlOWFRYw.I8V_GL5s2afZTh_ZMpshauGpnItx7iItBc6pgVRAOVg
```

It's sent as an HTTP header on every request:

```
Authorization: Bearer ory_at_hV2cm_iq55iipi...
```

That's the whole "authentication" part of Bindu: the client attaches a bearer token, the server validates it, and if it's good, the request goes through.

Two things follow from "whoever holds it, gets in":

1. **Treat tokens like passwords.** A leaked token is an open door. Don't paste them into chat apps, don't commit them to git, don't log them.
2. **Give them an expiration.** Bindu tokens last about one hour. If a token leaks, the damage window is bounded.

---

## Who issues the tokens? Meet Hydra

Now the obvious question: where does the bearer token come from? The agent certainly doesn't hand them out — that would be like asking the movie theatre door-checker to also run the ticket booth.

Instead, Bindu uses a separate service whose whole job is issuing and validating tokens. That service is [**Ory Hydra**](https://www.ory.sh/hydra/) — an open-source OAuth 2.0 server, battle-tested, used by lots of companies. We don't roll our own, because token issuance is easy to get subtly wrong and hard to review.

Hydra exposes itself as two different URLs:

| URL | Purpose | Who calls it |
|---|---|---|
| `https://hydra.getbindu.com` | **Public** — issues tokens to clients. Endpoints like `/oauth2/token`. | Clients (your code, Postman, the gateway) |
| `https://hydra-admin.getbindu.com` | **Admin** — registers clients, looks up what a token means. Endpoints like `/admin/*`. | Agents, registration scripts |

These are two listeners on the same Hydra process, backed by one shared database. Registering a client on admin is immediately visible to the token endpoint on public. That's why our flow works across two hostnames without any sync step.

> **Why two URLs?** The admin endpoints must never be exposed to the open internet. Anyone who can reach `/admin/clients` can register new clients or read secrets. In production, admin lives on a private network; only the public URL is reachable from outside.

---

## The flow, walked through

Here's what happens end to end when a client wants to talk to an agent.

```
┌─────────┐                  ┌──────────────┐              ┌──────────────┐              ┌───────┐
│ Client  │                  │ Hydra admin  │              │ Hydra public │              │ Agent │
└────┬────┘                  └──────┬───────┘              └──────┬───────┘              └───┬───┘
     │                              │                             │                          │
     │ 1. Register as OAuth client  │                             │                          │
     ├─────────────────────────────▶│                             │                          │
     │                              │                             │                          │
     │  201 Created                 │                             │                          │
     │◀─────────────────────────────┤                             │                          │
     │                              │                             │                          │
     │                              │                             │                          │
     │ 2. Exchange secret for a token                             │                          │
     ├────────────────────────────────────────────────────────────▶                          │
     │                              │                             │                          │
     │  access_token (valid ~1h)    │                             │                          │
     │◀────────────────────────────────────────────────────────────                          │
     │                              │                             │                          │
     │                              │                             │                          │
     │ 3. Call agent with Authorization: Bearer <token>           │                          │
     ├────────────────────────────────────────────────────────────────────────────────────▶ │
     │                              │                             │                          │
     │                              │ 4. Agent asks Hydra: "is this token valid?"           │
     │                              │◀─────────────────────────────────────────────────────┤
     │                              │                             │                          │
     │                              │   active=true, expires in X │                          │
     │                              ├─────────────────────────────────────────────────────▶│
     │                              │                             │                          │
     │  5. Response                 │                             │                          │
     │◀────────────────────────────────────────────────────────────────────────────────────┤
     │                              │                             │                          │
```

Three real-world steps, each with its own shape:

- **Step 1 (once per client)** — you introduce yourself to Hydra. Hydra records who you are and gives you a client secret. This happens rarely — usually once when a new client is provisioned.
- **Step 2 (once per hour)** — you trade your secret for a short-lived bearer token. The secret is long-lived; the token isn't.
- **Step 3–5 (every request)** — you attach the token to each request. The agent doesn't trust the token blindly; it asks Hydra to confirm it's still valid.

Step 4 is called **token introspection**. It's what makes Hydra's opaque tokens safe: the agent never reads the token itself, only asks Hydra what it means.

---

## What a token actually contains (and doesn't)

A Bindu bearer token looks random on purpose. It's **opaque** — a handle, not a document. Reading the string reveals nothing about who the user is. All the meaning lives in Hydra's database.

When the agent introspects a token, Hydra returns something like:

```json
{
  "active":     true,
  "client_id":  "did:bindu:dutta_raahul_at_gmail_com:postman:ee67868d-d4b6-...",
  "sub":        "did:bindu:dutta_raahul_at_gmail_com:postman:ee67868d-d4b6-...",
  "scope":      "openid offline agent:read agent:write",
  "exp":        1776622403,
  "iat":        1776618803,
  "token_type": "Bearer"
}
```

Read line by line:

- `active: true` — Hydra still considers this token valid. If the token has expired, been revoked, or was never issued, this flips to `false` and the request is rejected.
- `client_id` / `sub` — the identifier of the client this token was issued for. **This is usually a DID.** The DID page explains why.
- `scope` — the list of permissions this token carries. Think of scope as "which rooms of the house does this ticket let you into." `agent:read` gives read access; `agent:write` gives write access.
- `exp` — Unix timestamp when the token expires. After this, `active` becomes `false`.
- `iat` — when the token was issued.

The agent's middleware reads this object, decides whether to let the request through, and attaches the `client_id` to the incoming request's context so handlers know who's calling.

---

## Turning authentication on in Bindu

Authentication is **off by default** in development. To turn it on, set environment variables that tell Bindu which Hydra to talk to.

```bash
# Flip the master switch
AUTH__ENABLED=true

# We only support Hydra today
AUTH__PROVIDER=hydra

# Where your Hydra instances live
HYDRA__ADMIN_URL=https://hydra-admin.getbindu.com
HYDRA__PUBLIC_URL=https://hydra.getbindu.com
```

The double-underscore (`__`) is how Bindu flattens nested config into environment variables. `AUTH__ENABLED` maps to `settings.auth.enabled`, `HYDRA__ADMIN_URL` maps to `settings.hydra.admin_url`. You don't need to care about the mapping — just set them.

When your agent starts with these set, the middleware automatically:

1. Configures itself to talk to Hydra admin for introspection.
2. Rejects any incoming request without a valid `Authorization: Bearer ...` header.
3. Attaches the introspection result to the request so downstream code knows who's calling.

---

## Getting your first bearer token

### Step 1 — register your client with Hydra

Think of this like opening an account at a bank. You tell Hydra who you are, Hydra files the paperwork.

```bash
curl -X POST 'https://hydra-admin.getbindu.com/admin/clients' \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id":     "did:bindu:your_email_at_example_com:your_agent:<uuid>",
    "client_secret": "<pick a strong random value>",
    "grant_types":   ["client_credentials"],
    "response_types": ["token"],
    "scope":         "openid offline agent:read agent:write",
    "token_endpoint_auth_method": "client_secret_post"
  }'
```

A few words on each field:

- `client_id` — your agent's name in Hydra. In Bindu, this is always a **DID string** (see the DID page for why). Hydra treats it as any opaque identifier; the DID machinery adds meaning on top.
- `client_secret` — your password to get tokens. Generate 32 bytes of randomness:
  ```bash
  openssl rand -base64 32 | tr -d '=' | tr '+/' '-_'
  ```
  Store it like you'd store a database password. You need it again in step 2.
- `grant_types` — how you'll be getting tokens. `client_credentials` means "I'm a server, not a human in a browser" — no login forms, no redirects, just swap a secret for a token.
- `scope` — the permissions you want your tokens to carry. Don't request scopes you don't need.
- `token_endpoint_auth_method: client_secret_post` — says you'll send the secret in the request body (HTTP POST form), as opposed to in a header. Both are valid; we use `post` for compatibility with our code.

### Step 2 — exchange the secret for a token

Whenever your access token is about to expire (or the first time you need one), call:

```bash
curl -X POST 'https://hydra.getbindu.com/oauth2/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=did:bindu:your_email_at_example_com:your_agent:<uuid>' \
  -d 'client_secret=<the secret from step 1>' \
  -d 'scope=openid offline agent:read agent:write'
```

Response:

```json
{
  "access_token": "ory_at_...long opaque string...",
  "expires_in":   3599,
  "scope":        "openid offline agent:read agent:write",
  "token_type":   "bearer"
}
```

The `access_token` is your bearer token. Copy it. Don't log it. Store it in memory for the next ~hour; refresh when it gets close to expiring.

### Step 3 — use the token

```bash
curl --location 'http://localhost:3773/' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer ory_at_...' \
  --data '{
      "jsonrpc": "2.0",
      "method":  "message/send",
      "params":  { "message": { "role": "user", "content": "Hello!" } },
      "id":      1
  }'
```

If the agent responds with real data, your authentication works. If it rejects with a 401 or 403, the next section explains why.

---

## What can go wrong (and what each error means)

Errors are where newcomers lose the most time. Here's a map — if you see one of these, find it in the "cause" column and fix _that_, not something else.

| You see | Most likely cause | Fix |
|---|---|---|
| `401 Unauthorized`, no `Authorization` header | You forgot to attach the token | Add `Authorization: Bearer <token>` |
| `401 Unauthorized`, introspection says `active:false` | Token expired | Re-run step 2 to get a fresh token |
| `401 Unauthorized`, introspection says token doesn't exist | Token belongs to a different Hydra than the agent uses | Check `HYDRA__ADMIN_URL` — agent and client must point at the same Hydra |
| `invalid_client` at the token endpoint | Wrong `client_secret`, or wrong `client_id`, or the client doesn't exist on this Hydra | Register the client first, or double-check the secret |
| `invalid_scope` at the token endpoint | Requesting a scope the client wasn't registered with | Either register the client with more scopes, or request less |
| Token works for one endpoint, fails for another | The agent requires a specific scope you didn't request | Request the scope (e.g. `agent:write`) and get a new token |

A more subtle one, worth calling out:

> **Symptom:** introspection against one Hydra URL returns `active:true`, but the agent says the token is invalid.
>
> **Cause:** the agent is configured to talk to a _different_ Hydra instance than the one that issued the token. This happens when a dev machine's `HYDRA__ADMIN_URL` points at a local Hydra while the token came from production.
>
> **Fix:** make sure the `HYDRA__ADMIN_URL` the agent uses points at the same Hydra where you registered and got the token. Check the agent's startup log — it prints the admin URL it's using.

---

## Finding your credentials when you've lost them

Two things worth remembering:

- **Your agent's DID** is published in its agent card:
  ```bash
  curl http://localhost:3773/.well-known/agent.json
  ```
  The field `agent.did` (or similar) holds the DID — that's also the `client_id` for Hydra.

- **Your client secret** from `bindufy` is saved locally in `.bindu/oauth_credentials.json`. Treat that file like `.ssh/id_rsa` — read-only, user-only, never committed.

If you've lost the client secret entirely, register a fresh one via the admin API (`PUT /admin/clients/<client_id>` to replace it). The `PUT` rotation is documented alongside the DID setup.

---

## A word on the UI

The Bindu frontend has a Settings → Authentication page that can do step 2 for you. Enter your client secret, click a button, get a token. Useful when you're poking around with Postman or a browser extension. It's a convenience — not a replacement for understanding what's happening underneath.

---

## Where to go next

Authentication answers _"are you allowed in?"_ But in a world where one agent might ask another agent to do work on behalf of yet a third agent, you need a stronger question answered: _"are you really who you claim to be?"_ That's what DID signing handles.

Read on: [DID.md](./DID.md).

---

## Appendix: common commands

Register a client:

```bash
curl -X POST 'https://hydra-admin.getbindu.com/admin/clients' \
  -H 'Content-Type: application/json' \
  -d '{ ...see step 1 above... }'
```

Look up a client (does it exist? what metadata is set?):

```bash
curl 'https://hydra-admin.getbindu.com/admin/clients/<client_id>'
```

Update a client (rotate secret, update metadata):

```bash
curl -X PUT 'https://hydra-admin.getbindu.com/admin/clients/<client_id>' \
  -H 'Content-Type: application/json' \
  -d '{ ...full client record with changes... }'
```

Delete a client (be careful — breaks existing tokens):

```bash
curl -X DELETE 'https://hydra-admin.getbindu.com/admin/clients/<client_id>'
```

Introspect a token (debug "is this token valid?"):

```bash
curl -X POST 'https://hydra-admin.getbindu.com/admin/oauth2/introspect' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'token=<your access token>'
```

Generate a strong secret:

```bash
openssl rand -base64 32 | tr -d '=' | tr '+/' '-_'
```
