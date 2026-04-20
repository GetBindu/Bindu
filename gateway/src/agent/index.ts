import { Context, Effect, Layer } from "effect"
import { z } from "zod"
import { readdirSync, readFileSync, existsSync, statSync } from "fs"
import { resolve, basename } from "path"
import { splitFrontmatter } from "../skill"
import { Ruleset, fromConfig as permFromConfig } from "../permission"
import { Service as ConfigService } from "../config"

/**
 * Agent abstraction for the gateway.
 *
 * Pattern borrowed from OpenCode's agent module but narrower. Phase 1 mostly
 * has one agent: `planner`. Additional agents can be dropped into
 * `gateway/agents/*.md` with YAML frontmatter.
 *
 * Frontmatter:
 *   ---
 *   name: planner
 *   description: Planning gateway for multi-agent collab
 *   mode: primary
 *   model: openrouter/anthropic/claude-sonnet-4.6
 *   temperature: 0.3
 *   steps: 10
 *   permission:
 *     agent_call: "ask"
 *   bindu:
 *     expose: false
 *     skills: []
 *     callablePeers: []
 *   ---
 *   <system-prompt markdown body>
 *
 * The markdown body becomes the system prompt (joined with any config-level
 * `instructions` at session start by the planner module).
 */

export const BinduAgentBlock = z
  .object({
    expose: z.boolean().default(false),
    skills: z.array(z.string()).optional(),
    callablePeers: z.array(z.string()).optional(),
  })
  .partial()

export const Info = z.object({
  name: z.string(),
  description: z.string().optional(),
  mode: z.enum(["primary", "subagent", "all"]).default("primary"),
  model: z.string().optional(),
  temperature: z.number().optional(),
  topP: z.number().optional(),
  steps: z.number().int().positive().optional(),
  prompt: z.string().optional(),
  permission: z.array(
    z.object({
      permission: z.string(),
      pattern: z.string().default("*"),
      action: z.enum(["allow", "deny", "ask"]),
    }),
  ),
  bindu: BinduAgentBlock.optional(),
  variant: z.string().optional(),
  hidden: z.boolean().optional(),
})
export type Info = z.infer<typeof Info>

/** Parse a YAML frontmatter block value (shared with skill module). */
function parseYaml(src: string): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  const stack: { indent: number; obj: Record<string, unknown> }[] = [{ indent: -1, obj: out }]

  for (const rawLine of src.split(/\r?\n/)) {
    const line = rawLine.replace(/\s+$/, "")
    if (!line.trim() || line.trim().startsWith("#")) continue
    const indent = line.length - line.trimStart().length
    while (stack.length > 1 && indent <= stack[stack.length - 1].indent) stack.pop()
    const current = stack[stack.length - 1].obj

    const m = line.trim().match(/^([A-Za-z0-9_\-]+):\s*(.*)$/)
    if (!m) continue
    const key = m[1]
    const rest = m[2]

    if (rest === "") {
      const child: Record<string, unknown> = {}
      current[key] = child
      stack.push({ indent, obj: child })
      continue
    }

    current[key] = parseScalar(rest)
  }
  return out
}

function parseScalar(s: string): unknown {
  const t = s.trim()
  if (t === "true") return true
  if (t === "false") return false
  if (t === "null" || t === "~") return null
  if (/^-?\d+$/.test(t)) return Number(t)
  if (/^-?\d+\.\d+$/.test(t)) return Number(t)
  if (t.startsWith("[") && t.endsWith("]")) {
    const inner = t.slice(1, -1).trim()
    if (!inner) return []
    return inner
      .split(",")
      .map((x) => x.trim())
      .map((x) => (x.startsWith('"') || x.startsWith("'") ? x.slice(1, -1) : x))
  }
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1)
  }
  return t
}

export function parseAgentFile(path: string, raw: string): Info {
  const { frontmatter, body } = splitFrontmatter(raw)
  const fm = frontmatter ? parseYaml(frontmatter) : {}
  const nameFromFile = basename(path).replace(/\.md$/i, "")

  // Convert nested permission object to flat Ruleset.
  const permission: Ruleset = permFromConfig(fm.permission as Record<string, unknown> | undefined)

  const candidate = {
    name: (fm.name as string | undefined) ?? nameFromFile,
    description: fm.description as string | undefined,
    mode: (fm.mode as Info["mode"] | undefined) ?? "primary",
    model: fm.model as string | undefined,
    temperature: typeof fm.temperature === "number" ? fm.temperature : undefined,
    topP: typeof fm.topP === "number" ? fm.topP : undefined,
    steps: typeof fm.steps === "number" ? fm.steps : undefined,
    prompt: body.trim() || undefined,
    permission,
    bindu: fm.bindu,
    variant: fm.variant as string | undefined,
    hidden: fm.hidden as boolean | undefined,
  }

  const result = Info.safeParse(candidate)
  if (!result.success) {
    throw new Error(`agent: invalid frontmatter in ${path}: ${result.error.message}`)
  }
  return result.data
}

export function loadAgentsDir(dir: string): Info[] {
  if (!existsSync(dir)) return []
  const entries = readdirSync(dir, { withFileTypes: true })
  const out: Info[] = []
  for (const e of entries) {
    const p = resolve(dir, e.name)
    if (e.isDirectory()) {
      out.push(...loadAgentsDir(p))
      continue
    }
    if (!e.isFile() || !e.name.toLowerCase().endsWith(".md")) continue
    const raw = readFileSync(p, "utf8")
    try {
      out.push(parseAgentFile(p, raw))
    } catch (err) {
      throw new Error(`agent: failed to parse ${p}: ${(err as Error).message}`)
    }
  }
  return out
}

export interface Interface {
  readonly list: () => Effect.Effect<Info[]>
  readonly get: (name: string) => Effect.Effect<Info | undefined>
  /** Default agent name — falls back to "planner" or the first primary agent found. */
  readonly defaultAgent: () => Effect.Effect<string>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Agent") {}

export interface LayerOptions {
  /** Directories to scan for `*.md` agent configs. Defaults: `$CWD/agents`, `$CWD/gateway/agents`. */
  directories?: string[]
}

export function layer(options: LayerOptions = {}): Layer.Layer<Service, Error, ConfigService> {
  return Layer.effect(
    Service,
    Effect.gen(function* () {
      // Config is used to merge in agent entries declared via config file
      // (not just markdown files) — matches OpenCode's dual source pattern.
      const config = yield* (yield* ConfigService).get()

      const dirs = options.directories ?? [
        resolve(process.cwd(), "agents"),
        resolve(process.cwd(), "gateway", "agents"),
      ]

      const markdownAgents: Info[] = yield* Effect.try({
        try: () => {
          const all: Info[] = []
          for (const d of dirs) {
            if (!existsSync(d)) continue
            const s = statSync(d)
            if (!s.isDirectory()) continue
            all.push(...loadAgentsDir(d))
          }
          return all
        },
        catch: (e) => (e instanceof Error ? e : new Error(String(e))),
      })

      // Overlay config-level agent entries (config wins for overlapping names).
      const configAgents: Info[] = Object.entries(config.agent ?? {}).map(([name, entry]) => ({
        name,
        description: entry.description,
        mode: entry.mode ?? "primary",
        model: entry.model,
        temperature: entry.temperature,
        topP: entry.topP,
        steps: entry.steps,
        prompt: entry.prompt,
        permission: [],
      }))

      const byName = new Map<string, Info>()
      for (const a of markdownAgents) byName.set(a.name, a)
      for (const a of configAgents) {
        const existing = byName.get(a.name)
        byName.set(a.name, existing ? { ...existing, ...a, permission: existing.permission } : a)
      }

      const all = Array.from(byName.values())

      return Service.of({
        list: () => Effect.succeed(all.slice()),
        get: (name) => Effect.succeed(byName.get(name)),
        defaultAgent: () =>
          Effect.sync(() => {
            if (byName.has("planner")) return "planner"
            const primary = all.find((a) => a.mode === "primary" && !a.hidden)
            if (primary) return primary.name
            if (all.length > 0) return all[0].name
            throw new Error("agent: no agents configured (default requested)")
          }),
      })
    }),
  )
}
