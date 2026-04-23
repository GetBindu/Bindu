import { describe, it, expect } from "vitest"
import { readFileSync } from "fs"
import { resolve } from "path"
import { DIDDocument } from "../../src/bindu/protocol/agent-card"
import { verify, verifyArtifact } from "../../src/bindu/identity/verify"
import { primaryPublicKeyBase58 } from "../../src/bindu/identity/resolve"
import { Normalize } from "../../src/bindu/protocol"

const FIX = resolve(__dirname, "../../../scripts/dryrun-fixtures/echo-agent")
const read = (name: string) => JSON.parse(readFileSync(resolve(FIX, name), "utf8"))

describe("Bindu identity — signature verification against Phase 0 fixtures", () => {
  it("verifies the real signature on the captured artifact", async () => {
    const didDoc = DIDDocument.parse(read("did-doc.json"))
    const pub = primaryPublicKeyBase58(didDoc)
    expect(pub).toBeTruthy()

    const task = Normalize.fromWire("task", read("final-task.json")) as any
    const artifact = task.artifacts[0]
    expect(artifact.parts[0].kind).toBe("text")
    const sig = artifact.parts[0].metadata["did.message.signature"]
    expect(sig).toBeTruthy()

    const ok = await verify(artifact.parts[0].text, sig, pub!)
    expect(ok).toBe(true)
  })

  it("rejects a tampered signature", async () => {
    const didDoc = DIDDocument.parse(read("did-doc.json"))
    const pub = primaryPublicKeyBase58(didDoc)!
    const task = Normalize.fromWire("task", read("final-task.json")) as any
    const artifact = task.artifacts[0]
    const sig = artifact.parts[0].metadata["did.message.signature"]

    const tamperedText = artifact.parts[0].text + "X"
    const ok = await verify(tamperedText, sig, pub)
    expect(ok).toBe(false)
  })

  it("rejects a malformed signature", async () => {
    const didDoc = DIDDocument.parse(read("did-doc.json"))
    const pub = primaryPublicKeyBase58(didDoc)!
    const ok = await verify("hello", "notbase58!!!", pub)
    expect(ok).toBe(false)
  })

  it("verifyArtifact aggregates over parts", async () => {
    const didDoc = DIDDocument.parse(read("did-doc.json"))
    const pub = primaryPublicKeyBase58(didDoc)!
    const task = Normalize.fromWire("task", read("final-task.json")) as any
    const art = task.artifacts[0]

    const outcome = await verifyArtifact({
      parts: art.parts,
      publicKeyBase58: pub,
    })
    expect(outcome.ok).toBe(true)
    expect(outcome.signed).toBeGreaterThan(0)
    expect(outcome.verified).toBe(outcome.signed)
  })
})
