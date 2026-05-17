# Bindu Inbox

The human-visible layer of secured A2A communication — a three-pane inbox for watching agent traffic land, verifying signatures, and inspecting payloads.

Each row is a JSON-RPC message between two DIDs, threaded by `context_id` so multi-turn exchanges read like email.

## Run it

```bash
cd inbox
npm install
npm run dev
```

Opens at <http://127.0.0.1:3775>. Port map: `3773` bindufy agents · `3774` gateway · `3775` this UI · `3787` API (proxied via `/api/*`).

Requires a personal agent (server-spawned via the wizard) for outbound auth — see [Sending below](#sending).

## Using the inbox

![Inbox three-pane layout](./docs/inbox.png)

### Layout

| Pane | What it shows |
| --- | --- |
| **Left** | Folders (Inbox / Sent / Drafts / Archive), Contacts grouped into **Gateways** (orchestrators for multi-agent plans) and **Agents** (single-purpose A2A peers). Your operator identity sits at the bottom. |
| **Middle** | Thread list — newest first, one row per `context_id`. The count badge is messages in the thread. |
| **Right** | Selected thread, oldest message at top. State pills + DID per row; full message bodies render inline. Reply composer pinned at the bottom. |

### Sending

Click **Compose**, pick recipients:

- **One agent** → direct A2A `message/send` to that peer.
- **Two or more agents** → comms auto-spawns a gateway (see `gateway-spawned-*` in Contacts), forwards your prompt as a plan, and threads the per-agent tool calls back under one `context_id`.

Outbound calls are JWT-bearer + DID-signed using the personal agent's Hydra OAuth client. If the personal agent isn't running, sends fall back to `did:bindu:operator:local` and most peers will reject them (`-32009`).

### Reading a thread

Each row carries:

- **State pill** — `submitted` · `working` · `input-required` · `payment-required` · `auth-required` · `completed` · `failed`. Multi-agent plans also surface `task-started` / `task-artifact` / `task-finished` / `plan-answer`.
- **Trust pill** — `first-contact` (new peer) · `known` · `self` (your own agents / planner).
- **DID** of the counterparty — click to see the full agent card.
- Body text (artifacts, replies, errors) rendered inline; the `<remote_content>` wrapper is stripped for readability.

**Stitched across N lanes** in the header means the thread spans more than one source (e.g. your direct outbox + a gateway-spawned thread for the same `context_id`).

### Verify · Inspect

Top-right of the thread view:

- **Copy** — full thread to clipboard (markdown).
- **Verify** — re-run signature checks against the peer's published `publicKeyBase58`. Shows `signed / verified / unsigned` counts and the verification reason on failure.

The detail rail (click any row) has three tabs: **Glance** (operator summary + any action buttons for actionable states), **Verify** (signature, DID match, nonce), **Inspect** (raw JSON-RPC).

### Replying

Type in the box at the bottom of the open thread. `⌘↵` sends. Replies inherit the thread's `context_id` and resume the existing task if it's still open, refine it (with `referenceTaskIds`) if the task ended in a terminal state, or start fresh otherwise.

## Stack

React 19 · React Router v7 (SPA) · Vite 6 · Tailwind v4 · TanStack Query · Zustand · Phosphor icons · SQLite (events) via `better-sqlite3` · Hono on the API side.

## Attribution

Visual aesthetic inspired by [cloudflare/agentic-inbox](https://github.com/cloudflare/agentic-inbox) (Apache 2.0). See [NOTICE](./NOTICE).
