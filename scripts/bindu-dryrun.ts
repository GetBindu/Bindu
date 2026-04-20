#!/usr/bin/env bun
// Phase 0 protocol dry-run. Polling-first (Bindu task-first architecture).
// Flow: AgentCard -> DID Doc -> /agent/skills -> /agent/negotiation -> message/send -> poll tasks/get -> verify.
// See gateway/plans/phase-0-dryrun.md.

import { randomUUID } from "crypto"
import * as ed25519 from "@noble/ed25519"
import { sha512 } from "@noble/hashes/sha2.js"
import bs58 from "bs58"
import { writeFile, mkdir } from "fs/promises"
import { resolve, dirname } from "path"
import { fileURLToPath } from "url"

// @noble/ed25519 v2 needs sha512 hook set explicitly (no default).
ed25519.etc.sha512Sync = (...msgs) => sha512(ed25519.etc.concatBytes(...msgs))
ed25519.etc.sha512Async = async (...msgs) => sha512(ed25519.etc.concatBytes(...msgs))

const __dirname = dirname(fileURLToPath(import.meta.url))

const PEER = process.env.PEER_URL ?? "http://localhost:3773"
const TOKEN = process.env.PEER_JWT // optional
const FIXTURE_NAME = process.env.FIXTURE_NAME ?? "echo-agent"
const FIXTURES = resolve(__dirname, "dryrun-fixtures", FIXTURE_NAME)
await mkdir(FIXTURES, { recursive: true })

const headers = {
  "Content-Type": "application/json",
  ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
}

const notes: string[] = []
const note = (s: string) => {
  console.log(`  [note] ${s}`)
  notes.push(s)
}

function dump(name: string, data: unknown) {
  return writeFile(resolve(FIXTURES, name), JSON.stringify(data, null, 2))
}

async function maybeJson(resp: Response): Promise<any | null> {
  if (!resp.ok) return null
  try {
    return await resp.json()
  } catch {
    return null
  }
}

// -----------------------------------------------------------------
// 1. AgentCard
// -----------------------------------------------------------------
console.log(`\n== peer: ${PEER} ==\n`)
console.log("1. GET /.well-known/agent.json")
const cardResp = await fetch(`${PEER}/.well-known/agent.json`)
if (!cardResp.ok) {
  console.error(`AgentCard fetch failed: ${cardResp.status}`)
  process.exit(1)
}
const card = await cardResp.json()
await dump("agent-card.json", card)

console.log(`  name:            ${card.name}`)
console.log(`  id (DID):        ${card.id}`)
console.log(`  protocolVersion: ${card.protocolVersion}`)
console.log(`  streaming:       ${card.capabilities?.streaming}`)
console.log(`  pushNotifs:      ${card.capabilities?.pushNotifications}`)
console.log(`  skills:          ${(card.skills ?? []).map((s: any) => s.id).join(", ")}`)
console.log(`  securitySchemes: ${Object.keys(card.securitySchemes ?? {}).join(", ") || "(none)"}`)

if (!card.id?.startsWith("did:bindu") && !card.id?.startsWith("did:key")) {
  note(`AgentCard.id is not a DID: ${card.id}`)
}

// -----------------------------------------------------------------
// 2. DID Document (if peer has a DID)
// -----------------------------------------------------------------
console.log("\n2. POST /did/resolve")
let didDoc: any = null

// DID may be in id (rare) or in capabilities.extensions[].uri (observed in practice).
const didFromExtensions = (card.capabilities?.extensions ?? [])
  .map((e: any) => e.uri)
  .find((u: string) => typeof u === "string" && u.startsWith("did:"))
const didToResolve = card.id?.startsWith("did:") ? card.id : didFromExtensions

if (didToResolve) {
  console.log(`  resolving: ${didToResolve}`)
  if (!card.id?.startsWith("did:")) {
    note(`AgentCard.id is "${card.id}" (bare UUID); real DID found in capabilities.extensions[].uri`)
  }
  const resp = await fetch(`${PEER}/did/resolve`, {
    method: "POST",
    headers,
    body: JSON.stringify({ did: didToResolve }),
  })
  didDoc = await maybeJson(resp)
  if (didDoc) {
    await dump("did-doc.json", didDoc)
    const keys = didDoc.authentication?.map((a: any) => a.type).join(", ")
    console.log(`  authentication[]: ${keys}`)
    console.log(`  @context:         ${JSON.stringify(didDoc["@context"])}`)
  } else {
    console.log(`  /did/resolve failed or returned non-JSON (status ${resp.status})`)
    note(`/did/resolve not reachable`)
  }
} else {
  console.log(`  skipped (no DID on AgentCard)`)
}

// -----------------------------------------------------------------
// 3. /agent/skills
// -----------------------------------------------------------------
console.log("\n3. GET /agent/skills")
const skillsResp = await fetch(`${PEER}/agent/skills`, { headers })
const skills = await maybeJson(skillsResp)
if (skills) {
  await dump("skills.json", skills)
  const ids = (skills.skills ?? []).map((s: any) => s.id)
  console.log(`  ${ids.length} skill(s): ${ids.join(", ")}`)

  const first = ids[0]
  if (first) {
    const detResp = await fetch(`${PEER}/agent/skills/${first}`, { headers })
    const detail = await maybeJson(detResp)
    if (detail) {
      await dump(`skill-${first}.json`, detail)
      console.log(`  detail for ${first}: ${Object.keys(detail).join(", ")}`)
    } else {
      note(`/agent/skills/${first} returned ${detResp.status}`)
    }
  }
} else {
  console.log(`  /agent/skills failed (status ${skillsResp.status})`)
  note(`/agent/skills not reachable`)
}

// -----------------------------------------------------------------
// 4. /agent/negotiation (optional probe)
// -----------------------------------------------------------------
console.log("\n4. POST /agent/negotiation")
const negoResp = await fetch(`${PEER}/agent/negotiation`, {
  method: "POST",
  headers,
  body: JSON.stringify({
    task_summary: "say hello",
    input_mime_types: ["text/plain"],
    output_mime_types: ["text/plain", "application/json"],
  }),
})
const nego = await maybeJson(negoResp)
if (nego) {
  await dump("negotiation.json", nego)
  console.log(`  accepted: ${nego.accepted}, score: ${nego.score}, confidence: ${nego.confidence}`)
} else {
  console.log(`  /agent/negotiation failed (status ${negoResp.status})`)
  note(`/agent/negotiation not reachable`)
}

// -----------------------------------------------------------------
// 5. message/send
// -----------------------------------------------------------------
console.log("\n5. POST / method=message/send")
const contextId = randomUUID()
const taskId = randomUUID()
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
const submitResp = await fetch(`${PEER}/`, {
  method: "POST",
  headers,
  body: JSON.stringify(submitReq),
})
if (!submitResp.ok) {
  const body = await submitResp.text().catch(() => "")
  console.error(`message/send HTTP ${submitResp.status}: ${body}`)
  process.exit(1)
}
const submitted = await submitResp.json()
await dump("submit-response.json", submitted)

if (submitted.error) {
  console.error(`  error: ${submitted.error.code} ${submitted.error.message}`)
  note(`message/send returned JSON-RPC error ${submitted.error.code}`)
  process.exit(1)
}
const initialState = submitted.result?.status?.state
console.log(`  returned state: ${initialState}`)
console.log(`  server taskId : ${submitted.result?.id}`)
const serverTaskId = submitted.result?.id ?? taskId

// -----------------------------------------------------------------
// 6. Poll tasks/get until terminal
// -----------------------------------------------------------------
console.log("\n6. POST / method=tasks/get (poll loop)")
const TERMINAL = ["completed", "failed", "canceled", "rejected"]
const backoff = [500, 1000, 1000, 2000, 2000, 5000, 5000, 10000]
const MAX_POLLS = 30

let task: any = submitted.result
// Observed: the server expects camelCase `taskId` here, despite some OpenAPI
// specs using snake_case `task_id`. It returns -32700 (not -32602) on mismatch.
let pollCasing: "camel" | "snake" = "camel"

for (let i = 0; i < MAX_POLLS && !TERMINAL.includes(task?.status?.state); i++) {
  await new Promise((r) => setTimeout(r, backoff[Math.min(i, backoff.length - 1)]))

  const params = pollCasing === "camel" ? { taskId: serverTaskId } : { task_id: serverTaskId }

  const pollResp = await fetch(`${PEER}/`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "tasks/get",
      id: randomUUID(),
      params,
    }),
  })
  const raw = await pollResp.text()
  let payload: any = null
  try {
    payload = raw ? JSON.parse(raw) : null
  } catch {
    /* keep payload null */
  }

  if (!payload) {
    console.error(`  tasks/get non-JSON (HTTP ${pollResp.status}): ${raw.slice(0, 200)}`)
    note(`tasks/get returned non-JSON at poll ${i} (HTTP ${pollResp.status})`)
    // dump raw for diagnostics
    await writeFile(resolve(FIXTURES, `poll-${i}-raw.txt`), raw)
    break
  }

  // Some bindu builds return -32602 for schema mismatch; others return -32700 (misleading).
  // Accept either as a "wrong casing" signal and flip.
  if ((payload?.error?.code === -32602 || payload?.error?.code === -32700) && pollCasing === "camel") {
    note(`tasks/get rejected camelCase taskId; switching to snake_case task_id`)
    pollCasing = "snake"
    i--
    continue
  }
  if ((payload?.error?.code === -32602 || payload?.error?.code === -32700) && pollCasing === "snake") {
    note(`tasks/get rejected snake_case task_id; switching to camelCase taskId`)
    pollCasing = "camel"
    i--
    continue
  }
  if (payload?.error) {
    console.error(`  tasks/get error ${payload.error.code}: ${payload.error.message}`)
    note(`tasks/get returned error ${payload.error.code}: ${payload.error.message}`)
    break
  }
  task = payload.result
  console.log(`  poll ${i}: state=${task?.status?.state}`)
}

await dump("final-task.json", task)
console.log(`\n  final state:   ${task?.status?.state}`)
console.log(`  artifacts:     ${(task?.artifacts ?? []).length}`)
console.log(`  history msgs:  ${(task?.history ?? []).length}`)

// -----------------------------------------------------------------
// 7. Artifact + signature inspection
// -----------------------------------------------------------------
console.log("\n7. Artifact + signature inspection")
for (const art of task?.artifacts ?? []) {
  const artId = art.artifact_id ?? art.artifactId
  const parts = art.parts ?? []
  console.log(`  artifact ${artId} | name=${art.name} | parts=${parts.length}`)

  for (const [i, p] of parts.entries()) {
    const sig = p.metadata?.["did.message.signature"]
    console.log(`    part ${i}: kind=${p.kind} | text-len=${(p.text ?? "").length} | sig=${sig ? "yes" : "no"}`)
    if (sig && p.kind === "text" && didDoc) {
      const pub = didDoc.authentication?.[0]?.publicKeyBase58
      if (pub) {
        try {
          const ok = await ed25519.verify(
            bs58.decode(sig),
            new TextEncoder().encode(p.text),
            bs58.decode(pub),
          )
          console.log(`      sig verify: ${ok ? "OK" : "FAILED"}`)
          if (!ok) note(`signature verify FAILED on artifact ${artId} part ${i}`)
        } catch (e) {
          console.log(`      sig verify threw: ${e}`)
          note(`signature verify threw on artifact ${artId} part ${i}: ${e}`)
        }
      }
    } else if (p.kind === "text" && !sig) {
      note(`artifact ${artId} part ${i} has no did.message.signature`)
    }
  }
}

// -----------------------------------------------------------------
// 8. Casing + role audit
// -----------------------------------------------------------------
const roleInHistory = new Set<string>()
for (const m of task?.history ?? []) {
  if (m.role) roleInHistory.add(m.role)
}
console.log(`\n8. Role values observed in history: ${[...roleInHistory].join(", ") || "(none)"}`)
if (roleInHistory.has("assistant") && !roleInHistory.has("agent")) {
  note(`history uses role="assistant" (not "agent") — Phase 1 normalize must accept both`)
}

// Casing check on one artifact
const firstArt = task?.artifacts?.[0]
if (firstArt) {
  const hasSnake = "artifact_id" in firstArt
  const hasCamel = "artifactId" in firstArt
  console.log(`   artifact casing: artifact_id=${hasSnake} artifactId=${hasCamel}`)
  if (hasSnake && !hasCamel) note(`artifact uses snake_case artifact_id`)
  if (hasCamel && !hasSnake) note(`artifact uses camelCase artifactId`)
}
if (task?.context_id !== undefined) note(`task uses snake_case context_id`)
if (task?.contextId !== undefined) note(`task uses camelCase contextId`)

// -----------------------------------------------------------------
// NOTES.md
// -----------------------------------------------------------------
const notesPath = resolve(FIXTURES, "NOTES.md")
const notesBody = notes.length
  ? notes.map((n) => `- ${n}`).join("\n")
  : "_No anomalies observed._"
await writeFile(
  notesPath,
  `# Dry-run notes — ${FIXTURE_NAME}\n\nPeer: ${PEER}\nRun at: ${new Date().toISOString()}\nProtocol version: ${card.protocolVersion ?? "(unknown)"}\n\n## Observations\n\n${notesBody}\n`,
)

console.log(`\n== DONE ==`)
console.log(`Fixtures: ${FIXTURES}`)
console.log(`Notes:    ${notesPath}`)
console.log(`Final:    ${task?.status?.state}`)
console.log(`Anomalies: ${notes.length}`)
