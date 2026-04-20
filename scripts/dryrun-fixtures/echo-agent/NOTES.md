# Dry-run notes — echo-agent

**Peer:** `http://localhost:3773`
**Agent:** `echo_agent` (from `examples/beginner/echo_simple_agent.py`)
**Bindu version:** `2026.12.6.dev74+g7bc46c0bc.d20260412`
**Protocol version** (`AgentCard.protocolVersion`): `1.0.0`
**Run at:** 2026-04-17

Phase 0 target: validate the Bindu wire format end-to-end. All steps passed (`completed` state reached; signature verified OK).

---

## Findings that materially affect Phase 1 (Zod + normalize layer)

### 1. Wire casing is inconsistent — per-type map

| Type | Casing |
|---|---|
| `AgentCard` top-level | camelCase: `protocolVersion`, `defaultInputModes`, `defaultOutputModes`, `numHistorySessions`, `debugMode`, `debugLevel`, `agentTrust`, `extraData` |
| `AgentCard.skills[]` inline | camelCase: `documentationPath` |
| `Skill` from `/agent/skills/{id}` | **snake_case**: `input_modes`, `output_modes`, `capabilities_detail`, `allowed_tools`, `documentation_path`, `has_documentation` |
| `Task` top-level | mixed: snake `context_id`; flat `id`, `kind`, `status`, `history`, `artifacts` |
| `Task.history[]` (HistoryMessage) | **snake_case**: `message_id`, `context_id`, `task_id`, `reference_task_ids` |
| `Task.artifacts[]` (Artifact) | **snake_case**: `artifact_id` |
| `MessagePart` | flat: `kind`, `text`, `metadata` |
| Request `message/send params.message` | camelCase: `messageId`, `contextId`, `taskId`, `referenceTaskIds` |
| Request `tasks/get params` | camelCase: **`taskId`** (snake `task_id` → `-32700` — misleading!) |

**Phase 1 implication:** `src/bindu/protocol/normalize.ts` maps both directions. Emit camelCase on outbound `message/*` and `tasks/*` params; parse both casings on inbound; internally canonicalize to camelCase.

### 2. Error code `-32700` is overloaded

Bindu returns `-32700 JSONParseError` when the body is valid JSON but fails Pydantic schema validation (e.g., snake_case where alias is camelCase). Spec-proper code would be `-32602 InvalidParams`. Our `BinduError` mapper must treat `-32700` and `-32602` as interchangeable for schema-mismatch retry logic.

### 3. `AgentCard.id` is a bare UUID, not a DID

Example: `AgentCard.id = "438b4815-7ebe-d853-b95d-48b32b68fa3a"` — no `did:...` prefix.

The **real DID** lives at `AgentCard.capabilities.extensions[].uri` with a `did:bindu:...` prefix. Echo's only extension is the DID:
```json
{
  "uri": "did:bindu:gaurikasethi88_at_gmail_com:echo_agent:438b4815-7ebe-d853-b95d-48b32b68fa3a",
  "description": "DID-based identity for echo_agent",
  "required": false,
  "params": { "author": "...", "agent_name": "...", "agent_id": "438b4815-..." }
}
```

**Phase 1 implication:** `getPeerDID(agentCard)` checks `id` first, then scans `extensions[].uri` for the `did:` prefix.

### 4. DID agent-id segment is a UUID (32 hex chars with dashes)

Spec: `agent_id = sha256(public_key)[:32]` = 32 hex chars. Wire: rendered as a UUID (`438b4815-7ebe-d853-b95d-48b32b68fa3a`). Remove dashes → 32 hex chars → matches the spec. Parser must accept both forms.

### 5. DID Doc shape confirmed (matches `docs/DID.md` verbatim)

```json
{
  "@context": ["https://www.w3.org/ns/did/v1", "https://getbindu.com/ns/v1"],
  "id": "did:bindu:...",
  "created": "2026-04-17T18:08:17.821594+00:00",
  "authentication": [{
    "id": "did:bindu:...#key-1",
    "type": "Ed25519VerificationKey2020",
    "controller": "did:bindu:...",
    "publicKeyBase58": "7dNzT2ZzYKsibUFirPVWZheh2TGKZuy3fGdCkcq2f2RM"
  }]
}
```

### 6. Signature verification confirmed

- Signed bytes = **raw UTF-8 of `part.text`** — no canonical JSON, no JWS.
- Signature = Ed25519, base58-encoded.
- Location = `artifacts[].parts[].metadata["did.message.signature"]`.
- Verified with `@noble/ed25519` v2 + `@noble/hashes/sha2.js` → `sha512`.
- **Important:** `@noble/ed25519` v2 requires the caller to set `ed25519.etc.sha512Sync` / `etc.sha512Async` — no default.

### 7. Role enum confirmed — `"agent"` not `"assistant"`

`Task.history[]` contains both `role: "user"` (user input) and `role: "agent"` (agent response). Normalize layer relabels `agent → assistant` internally.

### 8. Auth is ambiently required — not declared in AgentCard

Even with `AgentCard.securitySchemes` absent, the JSON-RPC endpoint (`POST /`) enforces bearer auth by default, returning `-32009 AuthenticationRequired` on HTTP 401. For dev: `AUTH__ENABLED=false` env.

**Phase 1 implication:** Don't rely solely on AgentCard for auth requirement. If first `message/send` returns `-32009`, surface clearly ("peer requires auth but advertised none"). Phase 4 trust scoring should ding agents that mis-declare.

### 9. `/agent/negotiation` works — ready for Phase 5 Bucket C

Structured response: `{ accepted, score, confidence, rejection_reason, queue_depth, subscores: { skill_match, io_compatibility, load, cost, performance } }`. Rejected our "say hello" task (skill_match=0 because echo's skills are question-answering + pdf-processing). No speculation needed.

### 10. Skill IDs include a version suffix (`-v1`)

Echo's skills are `question-answering-v1` and `pdf-processing-v1` — not `question-answering`. AgentCard.skills[].id is the versioned form. SkillDetail has a separate `version` field.

### 11. `AgentCard.url` may be incomplete

Echo returned `"url": "http://localhost"` — no port. Real is `http://localhost:3773`. Either Bindu has a bug or AgentCard.url is hostname-only. Phase 1: prefer the peer URL the caller passed in the agent catalog over `AgentCard.url`.

### 12. `agentTrust` is a structured object, not a string

Wire shape (differs from the OpenAPI specs at bindus.directory that show `agentTrust: string`):
```json
{
  "identityProvider": "custom",
  "inheritedRoles": [],
  "creatorId": "system",
  "creationTimestamp": 1776449298,
  "trustVerificationRequired": false,
  "allowedOperations": {}
}
```
Zod: `z.union([z.string(), z.object({...}).passthrough()])`.

---

## What matched the plan as-written

- `message/send` → poll `tasks/get` → terminal `completed` — flow works ✓
- One artifact per completed task ✓
- Artifact name `"result"` ✓
- `@noble/ed25519` + `bs58` library choices work ✓
- TaskState on this agent: `submitted`, `completed` observed; Bindu extensions not exercised ✓
- DID Doc matches `docs/DID.md` spec ✓

## What needs adjustment in Phase 1 plan

1. **Default outbound params to camelCase**. Note `-32700` vs `-32602` confusion in Bindu error mapper.
2. **DID lookup via `capabilities.extensions[].uri`**, not just `AgentCard.id`.
3. **`@noble/ed25519` v2 setup** in Phase 1 Day 8 — add the `etc.sha512Sync/Async` hook assignment (one line).
4. **Don't trust `AgentCard.url`**; use the peer URL passed in the agent catalog.
5. **Don't trust `AgentCard.securitySchemes` alone** to decide auth needs; infer from first-call response.
6. **SkillDetail is snake_case throughout** — normalize when projecting to our tool registry.

---

## Fixtures captured (for Phase 1 test vectors)

| File | Bytes | Purpose |
|---|---|---|
| `agent-card.json` | 1654 | full AgentCard; drives AgentCard Zod schema |
| `did-doc.json` | 609 | DID Document; drives DID Doc parser |
| `skills.json` | 1844 | `/agent/skills` list response |
| `skill-question-answering-v1.json` | 8369 | richest SkillDetail shape observed |
| `negotiation.json` | 250 | NegotiationResponse shape |
| `submit-response.json` | 741 | Task in `submitted` state (camelCase params worked) |
| `final-task.json` | 1351 | terminal Task with artifact + signature |
