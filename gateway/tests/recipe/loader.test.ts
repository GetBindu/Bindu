import { describe, it, expect, beforeEach, afterEach } from "vitest"
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "fs"
import { resolve, join } from "path"
import { tmpdir } from "os"
import { loadRecipesDir, parseRecipeFile, fmt } from "../../src/recipe"

/**
 * Unit tests for the recipe loader.
 *
 * Covers the four drift risks the shape of the loader introduces:
 *   1. Both layouts (flat `foo.md` and nested `foo/RECIPE.md`) discovered
 *      in one scan and collated by name.
 *   2. Duplicate name across layouts fails loudly at load time — silent
 *      precedence would make behavior dependent on filesystem order.
 *   3. Empty or missing description is rejected by Zod — the progressive-
 *      disclosure contract needs a non-empty line to display.
 *   4. Output is sorted by name — the planner prompt relies on a stable
 *      order so prompt caching is effective across requests.
 */

describe("recipe loader", () => {
  let dir: string

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "bindu-recipe-test-"))
  })

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true })
  })

  const writeFlat = (name: string, frontmatter: string, body = "body") =>
    writeFileSync(resolve(dir, `${name}.md`), `---\n${frontmatter}\n---\n${body}\n`)

  const writeBundled = (dirName: string, frontmatter: string, body = "body", siblings: Record<string, string> = {}) => {
    const sub = resolve(dir, dirName)
    mkdirSync(sub, { recursive: true })
    writeFileSync(resolve(sub, "RECIPE.md"), `---\n${frontmatter}\n---\n${body}\n`)
    for (const [name, content] of Object.entries(siblings)) {
      const p = resolve(sub, name)
      mkdirSync(resolve(p, ".."), { recursive: true })
      writeFileSync(p, content)
    }
  }

  it("discovers both flat and bundled layouts in one scan", () => {
    writeFlat("alpha", "name: alpha\ndescription: flat one")
    writeBundled("beta", "name: beta\ndescription: bundled one", "body", {
      "scripts/check.sh": "#!/bin/sh\necho ok",
    })

    const list = loadRecipesDir(dir)
    expect(list.map((r) => r.name)).toEqual(["alpha", "beta"])
    expect(list[0].location.endsWith("alpha.md")).toBe(true)
    expect(list[1].location.endsWith("RECIPE.md")).toBe(true)
  })

  it("returns results sorted by name regardless of filesystem order", () => {
    writeFlat("zzz", "name: zzz\ndescription: z")
    writeFlat("mmm", "name: mmm\ndescription: m")
    writeFlat("aaa", "name: aaa\ndescription: a")

    const list = loadRecipesDir(dir)
    expect(list.map((r) => r.name)).toEqual(["aaa", "mmm", "zzz"])
  })

  it("throws when two recipes share the same name across layouts", () => {
    writeFlat("dup", "name: dup\ndescription: flat")
    writeBundled("dup-dir", "name: dup\ndescription: bundled")

    expect(() => loadRecipesDir(dir)).toThrow(/duplicate name "dup"/)
  })

  it("rejects empty description", () => {
    writeFlat("empty", "name: empty\ndescription: ")

    expect(() => loadRecipesDir(dir)).toThrow(/invalid frontmatter/)
  })

  it("falls back to filename stem when `name` is omitted", () => {
    writeFlat("fallback-name", "description: no explicit name")

    const list = loadRecipesDir(dir)
    expect(list[0].name).toBe("fallback-name")
  })

  it("returns an empty array when the directory does not exist", () => {
    expect(loadRecipesDir(resolve(dir, "missing"))).toEqual([])
  })

  it("parses tags and triggers as arrays; defaults both to []", () => {
    writeFlat(
      "with-meta",
      "name: with-meta\ndescription: d\ntags: [a, b, c]\ntriggers: [x]",
    )
    writeFlat("bare", "name: bare\ndescription: d")

    const list = loadRecipesDir(dir)
    const meta = list.find((r) => r.name === "with-meta")!
    const bare = list.find((r) => r.name === "bare")!
    expect(meta.tags).toEqual(["a", "b", "c"])
    expect(meta.triggers).toEqual(["x"])
    expect(bare.tags).toEqual([])
    expect(bare.triggers).toEqual([])
  })

  it("parseRecipeFile uses fallbackName only when frontmatter omits name", () => {
    const withName = parseRecipeFile("/x.md", "---\nname: explicit\ndescription: d\n---\nbody", "stem")
    const withoutName = parseRecipeFile("/x.md", "---\ndescription: d\n---\nbody", "stem")
    expect(withName.name).toBe("explicit")
    expect(withoutName.name).toBe("stem")
  })

  it("rejects recipe names that start with 'call_' (reserved for A2A tool ids)", () => {
    writeFlat("bad", "name: call_research_search\ndescription: visually collides with an A2A tool id")

    expect(() => loadRecipesDir(dir)).toThrow(/call_/)
  })

  it("ignores directories without a RECIPE.md file", () => {
    const sub = resolve(dir, "just-a-dir")
    mkdirSync(sub, { recursive: true })
    writeFileSync(resolve(sub, "notes.md"), "# some notes, not a recipe")

    expect(loadRecipesDir(dir)).toEqual([])
  })
})

describe("Recipe.fmt", () => {
  const sample = [
    {
      name: "alpha",
      description: "First recipe",
      tags: ["x"],
      triggers: [],
      location: "/tmp/alpha.md",
      content: "body-a",
    },
    {
      name: "beta",
      description: "Second recipe",
      tags: [],
      triggers: [],
      location: "/tmp/beta/RECIPE.md",
      content: "body-b",
    },
  ]

  it("verbose mode returns an XML block with both recipes and their locations", () => {
    const out = fmt(sample, { verbose: true })
    expect(out).toContain("<available_recipes>")
    expect(out).toContain("<name>alpha</name>")
    expect(out).toContain("<name>beta</name>")
    expect(out).toContain("file:///tmp/alpha.md")
    expect(out).toContain("file:///tmp/beta/RECIPE.md")
    expect(out).toContain("<tags>x</tags>")
  })

  it("terse mode returns a markdown bullet list with names and descriptions only", () => {
    const out = fmt(sample, { verbose: false })
    expect(out).toContain("## Available Recipes")
    expect(out).toContain("- **alpha**: First recipe")
    expect(out).toContain("- **beta**: Second recipe")
    expect(out).not.toContain("file://")
    expect(out).not.toContain("<tags>")
  })

  it("reports plainly when there are no recipes available", () => {
    expect(fmt([], { verbose: true })).toBe("No recipes are currently available.")
    expect(fmt([], { verbose: false })).toBe("No recipes are currently available.")
  })
})
