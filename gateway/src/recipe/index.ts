import { Context, Effect, Layer } from "effect"
import { readFileSync, readdirSync, statSync, existsSync } from "fs"
import { resolve, basename, dirname } from "path"
import { pathToFileURL } from "url"
import { z } from "zod"
import { splitFrontmatter, parseYaml } from "../_shared/util/frontmatter"
import { evaluate as permEvaluate, type Ruleset } from "../permission"
import type { Info as AgentInfo } from "../agent"

/**
 * Recipe loader for the gateway.
 *
 * Recipes are markdown playbooks the planner can lazy-load when a task
 * matches. Inspired by opencode's skill system (progressive disclosure:
 * metadata in context always, body only on demand). Renamed to `recipe`
 * because `skill` is already taken in the gateway for A2A SkillRequest
 * (an agent capability exposed via /plan).
 *
 * Directory layout — two supported shapes:
 *
 *   gateway/recipes/foo.md                     flat recipe, no bundled files
 *   gateway/recipes/bar/RECIPE.md              bundled recipe; siblings like
 *   gateway/recipes/bar/scripts/check.sh       scripts/, reference/, etc. are
 *   gateway/recipes/bar/reference/notes.md     surfaced to the planner when
 *                                              the recipe loads
 *
 * Frontmatter:
 *
 *   ---
 *   name: bar                       # required; falls back to file/dir stem
 *   description: One-line summary   # required (non-empty)
 *   tags: [research, orchestration] # optional
 *   triggers: [research, lookup]    # optional planner hints
 *   ---
 *   # Markdown body — the playbook itself.
 */

export const Info = z.object({
  // The `call_` prefix is reserved for A2A tool ids the planner builds as
  // `call_<agentName>_<skillId>`. A recipe named `call_research_search`
  // would render in the `load_recipe` tool description next to an
  // identically-named A2A tool, and the planner LLM has no way to tell
  // them apart by sight. Different namespaces technically — recipe names
  // are parameters of one tool, tool ids are tools — but the visual
  // collision is what matters. Reject at load time.
  name: z
    .string()
    .min(1)
    .refine((n) => !n.startsWith("call_"), {
      message: "recipe name must not start with \"call_\" — that prefix is reserved for A2A tool ids",
    }),
  description: z.string().min(1),
  tags: z.array(z.string()).default([]),
  triggers: z.array(z.string()).default([]),
  /** Absolute path to the recipe's markdown file. */
  location: z.string(),
  /** Full markdown body (after frontmatter). */
  content: z.string(),
})
export type Info = z.infer<typeof Info>

/** Parse a single recipe file. `fallbackName` is used if frontmatter omits `name`. */
export function parseRecipeFile(path: string, raw: string, fallbackName: string): Info {
  const { frontmatter, body } = splitFrontmatter(raw)
  const fm = frontmatter ? parseYaml(frontmatter) : {}

  const candidate = {
    name: (fm.name as string | undefined) ?? fallbackName,
    description: (fm.description as string | undefined) ?? "",
    tags: Array.isArray(fm.tags) ? (fm.tags as string[]) : [],
    triggers: Array.isArray(fm.triggers) ? (fm.triggers as string[]) : [],
    location: path,
    content: body.trim(),
  }

  const result = Info.safeParse(candidate)
  if (!result.success) {
    throw new Error(`recipe: invalid frontmatter in ${path}: ${result.error.message}`)
  }
  return result.data
}

/**
 * Scan one directory for recipes.
 *
 * Two patterns discovered:
 *   1. Any `*.md` at the top level → flat recipe (name defaults to filename stem).
 *   2. Any `<dir>/RECIPE.md` one level deep → bundled recipe (name defaults to
 *      the containing directory name).
 *
 * Case-insensitive on the `.md` extension. Symlinks are not followed — gateway
 * recipes are expected to be real files in the repo.
 *
 * Throws if two recipes share the same `name` — that's a config error, not a
 * warning; resolving silently would make it ambiguous which body gets loaded.
 */
export function loadRecipesDir(dir: string): Info[] {
  if (!existsSync(dir)) return []
  const s = statSync(dir)
  if (!s.isDirectory()) return []

  const out: Info[] = []
  const seen = new Map<string, string>()
  const addIfNew = (info: Info) => {
    const prior = seen.get(info.name)
    if (prior) {
      throw new Error(
        `recipe: duplicate name "${info.name}" — defined in both ${prior} and ${info.location}`,
      )
    }
    seen.set(info.name, info.location)
    out.push(info)
  }

  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name)

    // Flat pattern: `<name>.md`
    if (e.isFile() && e.name.toLowerCase().endsWith(".md")) {
      const raw = readFileSync(p, "utf8")
      addIfNew(parseRecipeFile(p, raw, basename(e.name).replace(/\.md$/i, "")))
      continue
    }

    // Bundled pattern: `<dir>/RECIPE.md`
    if (e.isDirectory()) {
      const nested = resolve(p, "RECIPE.md")
      if (existsSync(nested) && statSync(nested).isFile()) {
        const raw = readFileSync(nested, "utf8")
        addIfNew(parseRecipeFile(nested, raw, e.name))
      }
    }
  }

  return out.sort((a, b) => a.name.localeCompare(b.name))
}

export interface Interface {
  /** All recipes, sorted by name. */
  readonly list: () => Effect.Effect<Info[]>
  /** Single recipe by name. Undefined if not found. */
  readonly get: (name: string) => Effect.Effect<Info | undefined>
  /**
   * Recipes an agent is permitted to load. If `agent` is omitted, returns
   * the full list unfiltered (planner startup path, before we know the
   * agent). With an agent, rules keyed `permission: "recipe"` in the
   * agent's ruleset filter out anything resolving to `deny`.
   */
  readonly available: (agent?: AgentInfo) => Effect.Effect<Info[]>
  /** Distinct parent directories of discovered recipes. Used by the tool
   *  to enumerate bundled files. */
  readonly dirs: () => Effect.Effect<string[]>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Recipe") {}

export interface LayerOptions {
  /** Directories to scan. Default: `$CWD/recipes`, `$CWD/gateway/recipes`. */
  directories?: string[]
}

export function layer(options: LayerOptions = {}): Layer.Layer<Service, Error> {
  return Layer.effect(
    Service,
    Effect.gen(function* () {
      const dirs = options.directories ?? [
        resolve(process.cwd(), "recipes"),
        resolve(process.cwd(), "gateway", "recipes"),
      ]

      const recipes: Info[] = yield* Effect.try({
        try: () => {
          const all: Info[] = []
          for (const d of dirs) all.push(...loadRecipesDir(d))
          // loadRecipesDir catches dupes within one dir; also catch dupes
          // that span multiple scan roots (e.g. $CWD/recipes and
          // gateway/recipes both defining `foo`).
          const byName = new Map<string, Info>()
          for (const r of all) {
            const prior = byName.get(r.name)
            if (prior) {
              throw new Error(
                `recipe: duplicate name "${r.name}" across scan roots — ${prior.location} and ${r.location}`,
              )
            }
            byName.set(r.name, r)
          }
          return Array.from(byName.values()).sort((a, b) => a.name.localeCompare(b.name))
        },
        catch: (e) => (e instanceof Error ? e : new Error(String(e))),
      })

      const byName = new Map(recipes.map((r) => [r.name, r]))
      const distinctDirs = Array.from(new Set(recipes.map((r) => dirname(r.location))))

      return Service.of({
        list: () => Effect.succeed(recipes.slice()),
        get: (name) => Effect.succeed(byName.get(name)),
        dirs: () => Effect.succeed(distinctDirs.slice()),
        available: (agent?: AgentInfo) =>
          Effect.sync(() => {
            if (!agent) return recipes.slice()
            const rs: Ruleset = agent.permission
            return recipes.filter(
              (r) =>
                permEvaluate(rs, { permission: "recipe", target: r.name, defaultAction: "allow" }) !==
                "deny",
            )
          }),
      })
    }),
  )
}

/** Default layer using default scan directories. */
export const defaultLayer = layer()

/**
 * Render a list of recipes for the planner.
 *
 * `verbose: true`  → XML block suitable for the system prompt. Includes
 *                    name, description, location (file:// URL), and tags.
 * `verbose: false` → markdown bullet list suitable for the `load_recipe`
 *                    tool description (shorter, no locations).
 */
export function fmt(list: Info[], opts: { verbose: boolean }): string {
  if (list.length === 0) return "No recipes are currently available."

  if (opts.verbose) {
    return [
      "<available_recipes>",
      ...list.flatMap((r) => [
        "  <recipe>",
        `    <name>${r.name}</name>`,
        `    <description>${r.description}</description>`,
        `    <location>${pathToFileURL(r.location).href}</location>`,
        ...(r.tags.length > 0 ? [`    <tags>${r.tags.join(", ")}</tags>`] : []),
        "  </recipe>",
      ]),
      "</available_recipes>",
    ].join("\n")
  }

  return [
    "## Available Recipes",
    ...list.map((r) => `- **${r.name}**: ${r.description}`),
  ].join("\n")
}
