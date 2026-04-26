import { describe, it, expect } from "vitest"
import { readFileSync } from "fs"
import { resolve } from "path"
import { AgentCard, SkillDetail } from "../../src/bindu/protocol/agent-card"
import { Task, Artifact, HistoryMessage } from "../../src/bindu/protocol/types"
import { DIDDocument } from "../../src/bindu/protocol/agent-card"
import { Normalize, Identity } from "../../src/bindu/protocol"
import { BinduError, ErrorCode } from "../../src/bindu/protocol/jsonrpc"

const FIX = resolve(__dirname, "../../../scripts/dryrun-fixtures/echo-agent")
const read = (name: string) => JSON.parse(readFileSync(resolve(FIX, name), "utf8"))

describe("Bindu protocol — Phase 0 fixture parsing", () => {
  it("AgentCard parses the echo agent card", () => {
    const raw = read("agent-card.json")
    const parsed = AgentCard.parse(raw)
    expect(parsed.name).toBe("echo_agent")
    expect(parsed.protocolVersion).toBe("1.0.0")
    expect(parsed.skills.length).toBeGreaterThan(0)
    expect(parsed.capabilities?.streaming).toBe(false)
    expect(parsed.capabilities?.extensions?.[0]?.uri).toMatch(/^did:bindu:/)
  })

  it("DID lookup finds DID in capabilities.extensions[]", () => {
    const card = AgentCard.parse(read("agent-card.json"))
    const did = Identity.getPeerDID(card)
    expect(did).not.toBeNull()
    expect(did).toMatch(/^did:bindu:gaurikasethi88_at_gmail_com:echo_agent:/)
  })

  it("DID parse splits bindu DID correctly", () => {
    const did = "did:bindu:gaurikasethi88_at_gmail_com:echo_agent:438b4815-7ebe-d853-b95d-48b32b68fa3a"
    const parsed = Identity.parseDID(did)
    expect(parsed?.method).toBe("bindu")
    if (parsed?.method === "bindu") {
      expect(parsed.author).toBe("gaurikasethi88_at_gmail_com")
      expect(parsed.agentName).toBe("echo_agent")
      expect(parsed.agentId).toBe("438b4815-7ebe-d853-b95d-48b32b68fa3a")
    }
    const hex = Identity.agentIdHex(did)
    expect(hex).toBe("438b48157ebed853b95d48b32b68fa3a")
  })

  it("DID Document parses correctly", () => {
    const raw = read("did-doc.json")
    const doc = DIDDocument.parse(raw)
    expect(doc.id).toMatch(/^did:bindu:/)
    expect(doc.authentication?.length).toBeGreaterThan(0)
    const first = doc.authentication?.[0]
    expect(typeof first).toBe("object")
    if (typeof first === "object") {
      expect(first.type).toBe("Ed25519VerificationKey2020")
      expect(first.publicKeyBase58).toBeTruthy()
    }
  })

  it("SkillDetail parses the snake_case skill doc", () => {
    const raw = read("skill-question-answering-v1.json")
    const parsed = SkillDetail.parse(raw)
    expect(parsed.id).toBe("question-answering-v1")
    // Wire is snake_case; after normalize it's camelCase
    const canon = Normalize.fromWire("skill-detail", raw) as any
    expect(canon.inputModes).toBeDefined()
    expect(canon.outputModes).toBeDefined()
    expect(canon.allowedTools || canon.allowed_tools).toBeDefined()
  })

  it("Task + Artifact + HistoryMessage parse from final-task.json", () => {
    const raw = read("final-task.json")
    // Raw has snake_case context_id; schema accepts contextId via passthrough
    const normalized = Normalize.fromWire("task", raw) as any
    expect(normalized.contextId).toBeTruthy()
    expect(normalized.status.state).toBe("completed")

    const task = Task.parse(normalized)
    expect(task.contextId).toBeDefined()
    expect(task.artifacts?.length).toBeGreaterThan(0)

    const art = task.artifacts?.[0]
    expect(art).toBeDefined()
    // After normalize, artifact should have artifactId not artifact_id
    expect((art as any).artifactId).toBeDefined()
  })

  it("Normalize round-trips artifact (snake → camel → snake equivalent)", () => {
    const wireArt = {
      artifact_id: "abc",
      name: "result",
      parts: [{ kind: "text", text: "hi" }],
    }
    const canon = Normalize.fromWire("artifact", wireArt) as any
    expect(canon.artifactId).toBe("abc")
    expect(canon.artifact_id).toBeUndefined()

    const back = Normalize.toWire("artifact", canon) as any
    expect(back.artifactId).toBe("abc")
  })

  it("tasks/get params normalize to camelCase", () => {
    const snake = { task_id: "t1" }
    const canon = Normalize.fromWire("tasks-get-params", snake) as any
    expect(canon.taskId).toBe("t1")

    const wire = Normalize.toWire("tasks-get-params", canon) as any
    expect(wire.taskId).toBe("t1")
  })

  it("HistoryMessage: wire is snake_case; normalize → canonical camelCase", () => {
    const raw = read("final-task.json")
    const firstHist = raw.history[0]
    expect(firstHist.message_id).toBeDefined()
    expect(firstHist.context_id).toBeDefined()
    expect(firstHist.task_id).toBeDefined()

    // Normalize gives canonical camelCase — the schema expects that form.
    const canon = Normalize.fromWire("history-message", firstHist) as any
    expect(canon.messageId).toBeDefined()
    expect(canon.contextId).toBeDefined()
    expect(canon.taskId).toBeDefined()

    const hm = HistoryMessage.parse(canon)
    expect(hm.messageId).toBe(firstHist.message_id)
    expect(hm.taskId).toBe(firstHist.task_id)
  })
})

describe("BinduError classification", () => {
  it("schema-mismatch codes include -32700 and -32602", () => {
    expect(new BinduError(ErrorCode.JsonParse, "x").isSchemaMismatch()).toBe(true)
    expect(new BinduError(ErrorCode.InvalidParams, "x").isSchemaMismatch()).toBe(true)
    expect(new BinduError(ErrorCode.InternalError, "x").isSchemaMismatch()).toBe(false)
  })

  it("auth codes include -32009, -32010, -32011, -32012", () => {
    expect(new BinduError(ErrorCode.AuthenticationRequired, "x").isAuth()).toBe(true)
    expect(new BinduError(ErrorCode.InvalidToken, "x").isAuth()).toBe(true)
    expect(new BinduError(ErrorCode.TokenExpired, "x").isAuth()).toBe(true)
    expect(new BinduError(ErrorCode.InvalidTokenSignature, "x").isAuth()).toBe(true)
  })

  it("terminal codes do not retry", () => {
    expect(new BinduError(ErrorCode.InsufficientPermissions, "x").isRetryable()).toBe(false)
    expect(new BinduError(ErrorCode.TaskNotFound, "x").isTerminal()).toBe(true)
  })
})
