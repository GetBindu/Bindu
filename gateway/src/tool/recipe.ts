import { Effect } from "effect"
import { readdirSync, statSync } from "fs"
import { resolve, relative, basename } from "path"
import { pathToFileURL } from "url"
import { z } from "zod"
import type * as Recipe from "../recipe"
import { define, type Context as ToolContext, type Def, type ExecuteResult } from "./tool"

/**
 * load_recipe — the planner's gateway to progressive-disclosure playbooks.
 *
 * Only metadata (name + description) sits in the system prompt. When the
 * planner recognizes a task matches a recipe, it calls this tool with
 * `name: "<recipe-name>"` and gets the full markdown body plus a list of
 * bundled sibling files (for recipes stored as `<dir>/RECIPE.md`).
 *
 * Pattern borrowed from opencode's `SkillTool`; adapted to the gateway's
 * simpler Tool.Def shape (no Effect.fnUntraced, no ripgrep dep — plain fs
 * is enough for the tiny bundled-file enumeration we need).
 *
 * Permission gating is via `ctx.ask({ permission: "recipe", target: name })`.
 * That hook is optional on ToolContext in Phase 1; when it's unset (current
 * state, see session/prompt.ts wrapTool), the call is a no-op. When a real
 * permission UI lands, this tool inherits it without code change.
 */

const MAX_BUNDLED_FILES = 10

const Parameters = z.object({
  name: z
    .string()
    .min(1)
    .describe("The exact `name` of the recipe to load, drawn from the available list in this tool's description."),
})

/**
 * Build the dynamic tool description from the recipes this agent may load.
 *
 * Called once per plan (per session) — the list is already
 * permission-filtered by Recipe.available(agent). If `list` is empty, the
 * tool advertises that fact plainly so the planner doesn't guess names.
 */
export function describeRecipe(list: Recipe.Info[]): string {
  if (list.length === 0) {
    return "Load a specialized recipe (playbook) with domain-specific instructions for the current task. No recipes are currently available."
  }

  return [
    "Load a specialized recipe (playbook) with domain-specific instructions for the current task.",
    "",
    "When you recognize that a task matches one of the recipes listed below, call this tool with the recipe's `name` to pull the full playbook into the conversation. The recipe body may instruct you to dispatch to specific A2A agents in a specific order, handle A2A task states (input-required, payment-required, auth-required) in a specific way, or follow a specific format.",
    "",
    "Tool output is a <recipe_content name=\"...\"> block containing the recipe body and a list of bundled sibling files (for recipes stored as <dir>/RECIPE.md — scripts, reference docs, etc.).",
    "",
    "Available recipes:",
    "",
    ...list.map((r) => `- **${r.name}**: ${r.description}`),
  ].join("\n")
}

/**
 * Enumerate bundled sibling files for a recipe.
 *
 * Bundled files only exist for the nested layout (`recipes/<name>/RECIPE.md`)
 * — for flat recipes (`recipes/foo.md`) the siblings are OTHER recipes, not
 * bundled assets, so we skip the scan entirely.
 *
 * Capped at {@link MAX_BUNDLED_FILES} entries to keep the tool output small.
 * Recursive one level to surface `scripts/`, `reference/`, etc. without
 * dragging in node_modules-style deep trees.
 */
function listBundledFiles(recipeLocation: string): string[] {
  if (basename(recipeLocation).toUpperCase() !== "RECIPE.MD") return []

  const dir = resolve(recipeLocation, "..")
  const out: string[] = []

  const walk = (root: string, depth: number) => {
    if (out.length >= MAX_BUNDLED_FILES || depth > 2) return
    let entries: ReturnType<typeof readdirSync>
    try {
      entries = readdirSync(root, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      if (out.length >= MAX_BUNDLED_FILES) return
      const p = resolve(root, e.name)
      if (e.isDirectory()) {
        walk(p, depth + 1)
        continue
      }
      if (!e.isFile()) continue
      if (p === recipeLocation) continue
      out.push(p)
    }
  }

  walk(dir, 0)
  return out.sort()
}

/**
 * Build the load_recipe tool for a given planner agent.
 *
 * `available` is the permission-filtered list of recipes the planner is
 * allowed to load — passed in rather than recomputed so the tool
 * description matches the permission decision made at plan-start. `recipes`
 * is the live service interface used at execute() time to fetch the full
 * body.
 *
 * Execution contract:
 *
 *   - Unknown name → throws with the list of valid names
 *   - Known name → returns an ExecuteResult whose `.output` is a
 *     <recipe_content> block the planner can quote or follow verbatim
 *   - `ctx.ask` (if present) is consulted before the body is materialized;
 *     a rejection from the permission layer propagates unchanged
 */
export function buildLoadRecipeTool(
  recipes: Recipe.Interface,
  available: Recipe.Info[],
): Def {
  const description = describeRecipe(available)
  // Widened to ZodTypeAny so the returned Def unifies with the planner's
  // tool list (which carries heterogeneous parameter schemas). Narrow
  // parsing still happens inside execute via Parameters.parse(args).
  const parameters: z.ZodTypeAny = Parameters

  const info = define("load_recipe", {
    description,
    parameters,
    execute: (args: unknown, ctx: ToolContext) =>
      Effect.gen(function* () {
        const parsed = Parameters.parse(args)
        const recipe = yield* recipes.get(parsed.name)

        if (!recipe) {
          const all = yield* recipes.list()
          const names = all.map((r) => r.name).join(", ") || "none"
          return yield* Effect.fail(
            new Error(`load_recipe: recipe "${parsed.name}" not found. Available: ${names}`),
          )
        }

        // Permission gate — a no-op today (ctx.ask is optional and unset by
        // the current wrapTool), reserved for Phase 2 permission UI.
        if (ctx.ask) {
          yield* ctx.ask({ permission: "recipe", target: parsed.name })
        }

        const bundledFiles = listBundledFiles(recipe.location)
        const baseDir = resolve(recipe.location, "..")
        const baseUrl = pathToFileURL(baseDir).href

        const filesBlock =
          bundledFiles.length > 0
            ? [
                "<recipe_files>",
                ...bundledFiles.map((f) => `<file>${relative(baseDir, f)}</file>`),
                "</recipe_files>",
              ].join("\n")
            : "<recipe_files>(none)</recipe_files>"

        const output = [
          `<recipe_content name="${recipe.name}">`,
          `# Recipe: ${recipe.name}`,
          "",
          recipe.content,
          "",
          `Base directory for this recipe: ${baseUrl}`,
          "Relative paths (e.g., scripts/, reference/) resolve against this base directory.",
          bundledFiles.length >= MAX_BUNDLED_FILES
            ? `Note: bundled file list truncated at ${MAX_BUNDLED_FILES} entries.`
            : "",
          "",
          filesBlock,
          "</recipe_content>",
        ]
          .filter((l) => l !== "")
          .join("\n")

        const result: ExecuteResult = {
          title: `Loaded recipe: ${recipe.name}`,
          output,
          metadata: {
            name: recipe.name,
            dir: baseDir,
            fileCount: bundledFiles.length,
          },
        }
        return result
      }),
  })

  return {
    id: info.id,
    description,
    parameters,
    execute: (args: unknown, ctx: ToolContext) =>
      Effect.flatMap(info.init(), (init) => init.execute(args, ctx)),
  }
}
