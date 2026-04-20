# Phase 0 — Protocol Dry-Run

**Duration:** 1 day
**Repo impact:** zero (script + fixtures only, no core code changes)
**Goal:** Prove the Bindu wire format end-to-end before writing any production code. Capture real SSE fixtures to drive Phase 1 unit tests.

---

## Preconditions

- Bun ≥ 1.1 installed
- Python ≥ 3.12 (for running Bindu reference agent locally) OR a reachable Bindu-compatible agent URL
- Bindu reference agent running on `http://localhost:3773`
  - `pipx install bindu && bindu --agent echo` (or equivalent per Bindu docs)
  - Verify: `curl http://localhost:3773/.well-known/agent.json | jq '.name, .skills[].id'`
- Install deps (reused in Phase 1): `bun add -d @noble/ed25519 bs58 zod`

## In scope

- One file: `scripts/bindu-dryrun.ts` — single-file Bun script
- One directory: `scripts/dryrun-fixtures/` — captured JSON responses
- Verify: AgentCard parse, DID Doc parse, `message/send` + `tasks/get` poll loop, TaskStatus transitions, one-artifact-per-task semantics, `/agent/skills*` REST endpoints, `/agent/negotiation` probe, optional DID signature verification if peer signs

## Out of scope

- Any code inside `bindu/gateway/`
- Error handling beyond exit-on-failure
- SSE / `message/stream` (deployed agents don't ship this; Phase 2 work)
- OAuth2 client_credentials flow (script uses static bearer from env)
- mTLS

---

## Work breakdown

1. **Bootstrap** (5 min)
   ```bash
   cd /path/to/bindu-repo
   mkdir -p scripts/dryrun-fixtures/echo-agent
   ```
2. **Write `scripts/bindu-dryrun.ts`** (~200 LOC) — see code sketch below.
3. **Run against local echo agent** (2 min):
   ```bash
   PEER_URL=http://localhost:3773 bun scripts/bindu-dryrun.ts
   ```
4. **Capture fixtures** — script writes them:
   - `scripts/dryrun-fixtures/echo-agent/agent-card.json`
   - `scripts/dryrun-fixtures/echo-agent/did-doc.json`
   - `scripts/dryrun-fixtures/echo-agent/stream-001.sse`
5. **Re-run against other skills** (if available) → capture `stream-002.sse`, etc.
6. **Document anomalies** in `scripts/dryrun-fixtures/NOTES.md` — anything surprising (non-camelCase fields, unexpected states, missing sigs). Phase 1 Zod schemas read this file.

---

## Code sketch — `scripts/bindu-dryrun.ts`

```ts
#!/usr/bin/env bun
// Phase 0 protocol dry-run. Polling-first (Bindu's task-first architecture).
// Flow: AgentCard → optional DID Doc → /agent/skills → message/send → poll tasks/get → verify.

import { randomUUID } from "crypto"
import * as ed25519 from "@noble/ed25519"
import bs58 from "bs58"
import { writeFile, mkdir } from "fs/promises"
import { resolve } from "path"

const PEER  = process.env.PEER_URL  ?? "http://localhost:3773"
const TOKEN = process.env.PEER_JWT  // optional — some agents require bearer
const FIXTURES = resolve(import.meta.dir, "dryrun-fixtures/echo-agent")
await mkdir(FIXTURES, { recursive: true })

const headers = {
  "Content-Type": "application/json",
  ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
}

// 1. AgentCard ---------------------------------------------------
const card = await fetch(`${PEER}/.well-known/agent.json`).then((r) => {
  if (!r.ok) throw new Error(`AgentCard fetch failed: ${r.status}`)
  return r.json()
})
console.log("AgentCard:", card.name, "| protocol:", card.protocolVersion)
console.log("Streaming?", card.capabilities?.streaming, "| Push?", card.capabilities?.pushNotifications)
console.log("Skills:", card.skills?.map((s: any) => s.id).join(", "))
await writeFile(resolve(FIXTURES, "agent-card.json"), JSON.stringify(card, null, 2))

// 2. DID Document (optional) ------------------------------------
let didDoc: any = null
if (card.id?.startsWith("did:bindu")) {
  const resp = await fetch(`${PEER}/did/resolve`, {
    method: "POST", headers,
    body: JSON.stringify({ did: card.id }),
  })
  if (resp.ok) {
    didDoc = await resp.json()
    await writeFile(resolve(FIXTURES, "did-doc.json"), JSON.stringify(didDoc, null, 2))
    console.log("DID authentication:", didDoc.authentication?.map((a: any) => a.type))
  }
}

// 3. /agent/skills (richer than AgentCard summary) --------------
const skills = await fetch(`${PEER}/agent/skills`, { headers }).then(r => r.ok ? r.json() : null)
if (skills) {
  await writeFile(resolve(FIXTURES, "skills.json"), JSON.stringify(skills, null, 2))
  const first = skills.skills?.[0]?.id
  if (first) {
    const detail = await fetch(`${PEER}/agent/skills/${first}`, { headers }).then(r => r.ok ? r.json() : null)
    if (detail) await writeFile(resolve(FIXTURES, `skill-${first}.json`), JSON.stringify(detail, null, 2))
  }
}

// 4. (Optional) /agent/negotiation probe ------------------------
const nego = await fetch(`${PEER}/agent/negotiation`, {
  method: "POST", headers,
  body: JSON.stringify({
    task_summary: "say hello",
    input_mime_types: ["text/plain"],
    output_mime_types: ["text/plain", "application/json"],
  }),
}).then(r => r.ok ? r.json() : null)
if (nego) {
  await writeFile(resolve(FIXTURES, "negotiation.json"), JSON.stringify(nego, null, 2))
  console.log("Negotiation:", nego.accepted ? `accepted (score=${nego.score})` : `rejected (${nego.rejection_reason})`)
}

// 5. message/send (submit task, get task_id) --------------------
const taskId = randomUUID()
const contextId = randomUUID()
const submitReq = {
  jsonrpc: "2.0",
  method: "message/send",
  id: randomUUID(),
  params: {
    message: {
      messageId: randomUUID(),
      contextId,
      taskId,
      kind: "message",
      role: "user",
      parts: [{ kind: "text", text: "hello from dry-run" }],
    },
    configuration: { acceptedOutputModes: ["text/plain", "application/json"] },
  },
}
const submitResp = await fetch(`${PEER}/`, { method: "POST", headers, body: JSON.stringify(submitReq) })
if (!submitResp.ok) throw new Error(`message/send failed: ${submitResp.status}`)
const submitted = await submitResp.json()
await writeFile(resolve(FIXTURES, "submit-response.json"), JSON.stringify(submitted, null, 2))
console.log("Submitted. State:", submitted.result?.status?.state)

// 6. Poll tasks/get until terminal ------------------------------
const TERMINAL = ["completed", "failed", "canceled", "rejected"]
const backoff = [1000, 1000, 2000, 2000, 5000, 5000, 10000]
let task: any = null
for (let i = 0; i < 30; i++) {
  await new Promise(r => setTimeout(r, backoff[Math.min(i, backoff.length - 1)]))
  const pollResp = await fetch(`${PEER}/`, {
    method: "POST", headers,
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "tasks/get",
      id: randomUUID(),
      params: { task_id: taskId },
    }),
  })
  if (!pollResp.ok) throw new Error(`tasks/get failed: ${pollResp.status}`)
  task = (await pollResp.json()).result
  const state = task?.status?.state
  console.log(`poll ${i}: ${state}`)
  if (TERMINAL.includes(state)) break
}

await writeFile(resolve(FIXTURES, "final-task.json"), JSON.stringify(task, null, 2))

// 7. Inspect artifact(s) + verify signatures --------------------
for (const art of task.artifacts ?? []) {
  console.log("ARTIFACT", art.artifact_id, "| name:", art.name, "| parts:", art.parts?.length)
  if (didDoc) {
    const pub = didDoc.authentication?.[0]?.publicKeyBase58
    for (const p of art.parts ?? []) {
      const sig = p.metadata?.["did.message.signature"]
      if (sig && p.kind === "text" && pub) {
        const ok = await ed25519.verify(bs58.decode(sig), new TextEncoder().encode(p.text), bs58.decode(pub))
        console.log("  sig:", ok ? "OK" : "FAILED")
      } else if (p.kind === "text") {
        console.log("  (no signature on this part)")
      }
    }
  }
}

console.log(`\nFixtures: ${FIXTURES}`)
console.log(`Final state: ${task?.status?.state}`)
```

**Captured fixtures** (drive Phase 1 Zod schemas + tests):
- `agent-card.json` — real AgentCard shape
- `did-doc.json` — real DID Document (if peer declares DID)
- `skills.json`, `skill-{id}.json` — `/agent/skills*` responses
- `negotiation.json` — negotiation response (if peer supports)
- `submit-response.json` — initial `Task { state: submitted }`
- `final-task.json` — terminal `Task` with artifacts

---

## Test plan

**Manual — this is the whole phase:**

1. `bun scripts/bindu-dryrun.ts` against `http://localhost:3773`
2. Verify stdout contains: AgentCard name, ≥1 status transition, ≥1 complete artifact, terminal state
3. Verify `scripts/dryrun-fixtures/echo-agent/` contains `agent-card.json`, `did-doc.json`, `stream-001.sse`
4. If the agent signs artifacts, verify `sig verify: OK` appears for at least one part

**Sanity checks against captured fixtures:**
```bash
jq '.skills | length'            scripts/dryrun-fixtures/echo-agent/agent-card.json   # > 0
jq -r '.authentication[0].type'  scripts/dryrun-fixtures/echo-agent/did-doc.json      # Ed25519VerificationKey2020
jq -r '.status.state'            scripts/dryrun-fixtures/echo-agent/final-task.json   # completed
jq '.artifacts | length'         scripts/dryrun-fixtures/echo-agent/final-task.json   # >= 1
jq -r '.artifacts[0].parts[0].kind' scripts/dryrun-fixtures/echo-agent/final-task.json  # text
```

---

## Phase-specific risks

| Risk | Mitigation |
|---|---|
| Bindu reference returns newer `protocolVersion` than our Zod schemas cover | Script parses permissively; note version in `NOTES.md`; Phase 1 schemas use `z.passthrough()` + `.unknown()` |
| Wire casing (snake vs camel) differs from our assumptions | Script logs every unexpected field; `NOTES.md` captures the per-agent variance that drives Phase 1 normalize layer |
| DID signatures missing on artifacts | Log + continue; decide Phase 1 policy (fail-closed vs warn-and-allow) |
| Task never reaches terminal (max 30 polls exhausts) | Probably a broken peer or worker stall; log and fail; manual investigation |
| `tasks/get` param name casing — `task_id` vs `taskId` | Try both if the first returns `-32602`; record the working form in NOTES.md |
| Peer requires auth but `PEER_JWT` not set | Script returns HTTP 401; set the env var; document how JWT is acquired |
| Peer supports `message/stream` — should we test it? | Phase 0 stays polling-only. Note `capabilities.streaming: true` in NOTES.md; Phase 2 adds a streaming dry-run variant |

---

## Exit gate

- `bun scripts/bindu-dryrun.ts` exits with status 0
- Fixtures captured in `scripts/dryrun-fixtures/echo-agent/`
- Surprises documented in `scripts/dryrun-fixtures/NOTES.md`
- → Proceed to Phase 1 with confidence in the wire format
