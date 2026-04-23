/**
 * Tests for the boot-time identity loader. Keeps the partial-env
 * misconfig fail-fast behavior from regressing silently.
 *
 * Why this matters: half-loaded identity is the worst of all worlds.
 * The gateway would start fine, then produce mysterious 403s the
 * moment anything touches a did_signed peer. Better to refuse boot.
 */

import { describe, it, expect, afterEach } from "vitest"
import { setupHydraIntegration, tryLoadIdentity } from "../src/index"
import { loadLocalIdentity } from "../src/bindu/identity/local"

const SEED_VAR = "BINDU_GATEWAY_DID_SEED"
const AUTHOR_VAR = "BINDU_GATEWAY_AUTHOR"
const NAME_VAR = "BINDU_GATEWAY_NAME"

function clearIdentityEnv() {
  delete process.env[SEED_VAR]
  delete process.env[AUTHOR_VAR]
  delete process.env[NAME_VAR]
}

describe("tryLoadIdentity", () => {
  afterEach(clearIdentityEnv)

  it("returns undefined when all three env vars are unset", () => {
    clearIdentityEnv()
    expect(tryLoadIdentity()).toBeUndefined()
  })

  it("throws clear error when seed is set but author+name are missing", () => {
    clearIdentityEnv()
    process.env[SEED_VAR] = Buffer.from(new Uint8Array(32)).toString("base64")
    expect(() => tryLoadIdentity()).toThrow(/Partial DID identity config/)
  })

  it("throws clear error when author is set but seed+name are missing", () => {
    clearIdentityEnv()
    process.env[AUTHOR_VAR] = "ops@example.com"
    expect(() => tryLoadIdentity()).toThrow(/Partial DID identity config/)
  })

  it("loads a working identity when all three are set", () => {
    clearIdentityEnv()
    process.env[SEED_VAR] = Buffer.from(new Uint8Array(32)).toString("base64")
    process.env[AUTHOR_VAR] = "ops@example.com"
    process.env[NAME_VAR] = "gateway"
    const id = tryLoadIdentity()
    expect(id).toBeDefined()
    expect(id!.did).toMatch(/^did:bindu:ops_at_example_com:gateway:/)
  })

  it("surfaces seed malformation clearly when author+name are valid", () => {
    clearIdentityEnv()
    process.env[SEED_VAR] = "not-base64!"
    process.env[AUTHOR_VAR] = "ops@example.com"
    process.env[NAME_VAR] = "gateway"
    expect(() => tryLoadIdentity()).toThrow(/32 bytes/)
  })
})

// -----------------------------------------------------------------------
// setupHydraIntegration — partial-config fail-fast
// -----------------------------------------------------------------------

const ADMIN_VAR = "BINDU_GATEWAY_HYDRA_ADMIN_URL"
const TOKEN_VAR = "BINDU_GATEWAY_HYDRA_TOKEN_URL"
const SCOPE_VAR = "BINDU_GATEWAY_HYDRA_SCOPE"

function clearHydraEnv() {
  delete process.env[ADMIN_VAR]
  delete process.env[TOKEN_VAR]
  delete process.env[SCOPE_VAR]
}

describe("setupHydraIntegration", () => {
  afterEach(() => {
    clearIdentityEnv()
    clearHydraEnv()
  })

  function mkIdentity() {
    process.env[SEED_VAR] = Buffer.from(new Uint8Array(32)).toString("base64")
    process.env[AUTHOR_VAR] = "ops@example.com"
    process.env[NAME_VAR] = "gateway"
    return loadLocalIdentity({ author: "ops@example.com", name: "gateway" })
  }

  it("returns undefined when no Hydra env vars are set", async () => {
    clearHydraEnv()
    const identity = mkIdentity()
    expect(await setupHydraIntegration(identity)).toBeUndefined()
  })

  it("throws on partial config — admin set without token", async () => {
    clearHydraEnv()
    process.env[ADMIN_VAR] = "http://hydra:4445"
    const identity = mkIdentity()
    await expect(setupHydraIntegration(identity)).rejects.toThrow(
      /Partial Hydra config/,
    )
  })

  it("throws on partial config — token set without admin", async () => {
    clearHydraEnv()
    process.env[TOKEN_VAR] = "http://hydra:4444/oauth2/token"
    const identity = mkIdentity()
    await expect(setupHydraIntegration(identity)).rejects.toThrow(
      /Partial Hydra config/,
    )
  })
})
