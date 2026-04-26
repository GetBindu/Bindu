import { describe, it, expect, beforeEach, afterEach } from "vitest"
import { Effect } from "effect"
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "fs"
import { resolve, join } from "path"
import { tmpdir } from "os"
import type * as Recipe from "../../src/recipe"
import { buildLoadRecipeTool, describeRecipe } from "../../src/tool/recipe"
import type { Context as ToolContext } from "../../src/tool/tool"

/**
 * Unit tests for the load_recipe tool.
 *
 * Invariants we want pinned:
 *   1. The tool description is a function of the permission-filtered list
 *      we hand the factory — not the full service.all(). The planner
 *      passes the filtered list and expects the LLM to see only those
 *      names.
 *   2. Unknown names produce an error that includes the full available
 *      list, so the planner can recover by picking a real name.
 *   3. Known names produce a <recipe_content> envelope with a <recipe_files>
 *      block — this is the contract the planner relies on to quote body
 *      verbatim and find bundled assets.
 *   4. Flat recipes (no sibling dir) yield an empty files block, not a
 *      scan of other recipes in the same directory.
 */

type Info = Recipe.Info

const mkInfo = (overrides: Partial<Info> = {}): Info => ({
  name: overrides.name ?? "sample",
  description: overrides.description ?? "Sample recipe",
  tags: overrides.tags ?? [],
  triggers: overrides.triggers ?? [],
  location: overrides.location ?? "/tmp/sample.md",
  content: overrides.content ?? "Sample body.",
})

/** Minimal Recipe.Interface backed by a plain array. */
const mkFakeService = (recipes: Info[]): Recipe.Interface => ({
  list: () => Effect.succeed(recipes.slice()),
  get: (name) => Effect.succeed(recipes.find((r) => r.name === name)),
  available: () => Effect.succeed(recipes.slice()),
  dirs: () => Effect.succeed(Array.from(new Set(recipes.map((r) => r.location.replace(/\/[^/]+$/, ""))))),
})

const mkCtx = (): ToolContext => ({
  sessionId: "sess",
  messageId: "msg",
  agent: "planner",
  callId: "call",
  abort: new AbortController().signal,
  metadata: () => Effect.void,
})

describe("describeRecipe", () => {
  it("advertises every recipe in the filtered list with name and description", () => {
    const out = describeRecipe([
      mkInfo({ name: "alpha", description: "first" }),
      mkInfo({ name: "beta", description: "second" }),
    ])
    expect(out).toContain("alpha")
    expect(out).toContain("first")
    expect(out).toContain("beta")
    expect(out).toContain("second")
    // The planner relies on this phrase to know the tool exists at all.
    expect(out).toContain("Load a specialized recipe")
  })

  it("reports plainly when the filtered list is empty (no names to guess)", () => {
    const out = describeRecipe([])
    expect(out).toContain("No recipes are currently available")
    expect(out).not.toContain("- **") // no bullet entries
  })
})

describe("buildLoadRecipeTool", () => {
  let tmp: string

  beforeEach(() => {
    tmp = mkdtempSync(join(tmpdir(), "bindu-tool-test-"))
  })

  afterEach(() => {
    rmSync(tmp, { recursive: true, force: true })
  })

  it("exposes the description produced by describeRecipe on the returned Def", () => {
    const svc = mkFakeService([mkInfo({ name: "a", description: "aaa" })])
    const def = buildLoadRecipeTool(svc, [mkInfo({ name: "a", description: "aaa" })])
    expect(def.id).toBe("load_recipe")
    expect(def.description).toContain("a")
    expect(def.description).toContain("aaa")
  })

  it("returns a helpful error when the requested recipe does not exist", async () => {
    const svc = mkFakeService([
      mkInfo({ name: "known-1" }),
      mkInfo({ name: "known-2" }),
    ])
    const def = buildLoadRecipeTool(svc, [])
    const run = Effect.runPromise(def.execute({ name: "nope" }, mkCtx()))
    await expect(run).rejects.toThrow(/not found. Available: known-1, known-2/)
  })

  it("wraps body in <recipe_content> with an empty files block for flat recipes", async () => {
    const info = mkInfo({
      name: "flat",
      location: "/tmp/flat.md", // flat layout
      content: "The body of the flat recipe.",
    })
    const svc = mkFakeService([info])
    const def = buildLoadRecipeTool(svc, [info])

    const result = await Effect.runPromise(def.execute({ name: "flat" }, mkCtx()))
    expect(result.title).toBe("Loaded recipe: flat")
    expect(result.output).toContain('<recipe_content name="flat">')
    expect(result.output).toContain("# Recipe: flat")
    expect(result.output).toContain("The body of the flat recipe.")
    expect(result.output).toContain("<recipe_files>(none)</recipe_files>")
    expect(result.output).toContain("</recipe_content>")
    expect(result.metadata.fileCount).toBe(0)
  })

  it("enumerates sibling files for bundled (<dir>/RECIPE.md) recipes", async () => {
    const bundleDir = resolve(tmp, "bundled")
    mkdirSync(bundleDir, { recursive: true })
    mkdirSync(resolve(bundleDir, "scripts"), { recursive: true })
    const recipePath = resolve(bundleDir, "RECIPE.md")
    writeFileSync(recipePath, "---\nname: bundled\ndescription: b\n---\nbody")
    writeFileSync(resolve(bundleDir, "scripts/run.sh"), "#!/bin/sh")
    writeFileSync(resolve(bundleDir, "reference.md"), "ref")

    const info = mkInfo({ name: "bundled", location: recipePath, content: "body" })
    const svc = mkFakeService([info])
    const def = buildLoadRecipeTool(svc, [info])

    const result = await Effect.runPromise(def.execute({ name: "bundled" }, mkCtx()))
    expect(result.output).toContain("<recipe_files>")
    expect(result.output).toContain("<file>reference.md</file>")
    expect(result.output).toContain("<file>scripts/run.sh</file>")
    expect(result.output).not.toContain("<file>RECIPE.md</file>")
    expect(result.metadata.fileCount).toBe(2)
  })

  it("caps bundled-file enumeration at 10 entries", async () => {
    const bundleDir = resolve(tmp, "big")
    mkdirSync(bundleDir, { recursive: true })
    const recipePath = resolve(bundleDir, "RECIPE.md")
    writeFileSync(recipePath, "---\nname: big\ndescription: d\n---\nbody")
    for (let i = 0; i < 25; i++) {
      writeFileSync(resolve(bundleDir, `f${i}.txt`), "x")
    }

    const info = mkInfo({ name: "big", location: recipePath })
    const svc = mkFakeService([info])
    const def = buildLoadRecipeTool(svc, [info])

    const result = await Effect.runPromise(def.execute({ name: "big" }, mkCtx()))
    expect(result.metadata.fileCount).toBe(10)
    expect(result.output).toContain("truncated at 10 entries")
  })

  it("calls ctx.ask when provided, passing permission='recipe' and the recipe name as target", async () => {
    const info = mkInfo({ name: "perm", location: "/tmp/perm.md" })
    const svc = mkFakeService([info])
    const def = buildLoadRecipeTool(svc, [info])

    const calls: Array<{ permission: string; target?: string }> = []
    const ctx: ToolContext = {
      ...mkCtx(),
      ask: (input) =>
        Effect.sync(() => {
          calls.push(input)
        }),
    }

    await Effect.runPromise(def.execute({ name: "perm" }, ctx))
    expect(calls).toEqual([{ permission: "recipe", target: "perm" }])
  })
})
