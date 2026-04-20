import { Context, Effect, Layer } from "effect"
import { readFileSync, readdirSync, statSync, existsSync } from "fs"
import { resolve, basename } from "path"
import { z } from "zod"

/**
 * Skill loader for the gateway.
 *
 * Pattern borrowed from OpenCode's skill module but narrower: we just scan
 * one skills directory (or a list of them), read `*.md` files with YAML
 * frontmatter, and hand back a typed Info record. No discovery over XDG
 * paths, no HTTP fetches, no plugin hooks — the gateway's skill library is
 * small and static at boot.
 *
 * Directory layout expected:
 *   gateway/skills/research-summary.md
 *   gateway/skills/draft-review.md
 *
 * Frontmatter fields:
 *   ---
 *   name: research-summary               (required; falls back to filename stem)
 *   description: One-line summary        (required)
 *   tags: [research, summary]            (optional)
 *   bindu:                               (optional, for Phase 2+ expose)
 *     expose: true
 *     inputModes: [text/plain]
 *     outputModes: [application/json]
 *   ---
 *   # Markdown body...
 */

export const BinduExposeFrontmatter = z.object({
  expose: z.boolean().default(false),
  inputModes: z.array(z.string()).optional(),
  outputModes: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  assessment: z
    .object({
      keywords: z.array(z.string()).optional(),
      antiPatterns: z.array(z.string()).optional(),
      specializations: z.array(z.string()).optional(),
    })
    .partial()
    .optional(),
})

export const Info = z.object({
  name: z.string(),
  description: z.string(),
  tags: z.array(z.string()).default([]),
  location: z.string(),
  content: z.string(),
  bindu: BinduExposeFrontmatter.optional(),
})
export type Info = z.infer<typeof Info>

/** Extract YAML frontmatter from a markdown string. Returns [frontmatter, body]. */
export function splitFrontmatter(raw: string): { frontmatter: string | null; body: string } {
  if (!raw.startsWith("---")) return { frontmatter: null, body: raw }
  const end = raw.indexOf("\n---", 3)
  if (end === -1) return { frontmatter: null, body: raw }
  const frontmatter = raw.slice(3, end).replace(/^\r?\n/, "")
  const bodyStart = raw.indexOf("\n", end + 4)
  const body = bodyStart >= 0 ? raw.slice(bodyStart + 1) : ""
  return { frontmatter, body }
}

/** Minimal YAML parser (key: value + nested + arrays in inline `[a, b]` form). */
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

export function parseSkillFile(path: string, raw: string): Info {
  const { frontmatter, body } = splitFrontmatter(raw)
  const fm = frontmatter ? parseYaml(frontmatter) : {}
  const nameFromFile = basename(path).replace(/\.md$/i, "")

  const candidate = {
    name: (fm.name as string | undefined) ?? nameFromFile,
    description: (fm.description as string | undefined) ?? "",
    tags: Array.isArray(fm.tags) ? (fm.tags as string[]) : [],
    location: path,
    content: body.trim(),
    bindu: fm.bindu,
  }

  const result = Info.safeParse(candidate)
  if (!result.success) {
    throw new Error(`skill: invalid frontmatter in ${path}: ${result.error.message}`)
  }
  return result.data
}

export function loadSkillsDir(dir: string): Info[] {
  if (!existsSync(dir)) return []
  const entries = readdirSync(dir, { withFileTypes: true })
  const out: Info[] = []
  for (const e of entries) {
    const p = resolve(dir, e.name)
    if (e.isDirectory()) {
      out.push(...loadSkillsDir(p))
      continue
    }
    if (!e.isFile() || !e.name.toLowerCase().endsWith(".md")) continue
    const raw = readFileSync(p, "utf8")
    try {
      out.push(parseSkillFile(p, raw))
    } catch (err) {
      throw new Error(`skill: failed to parse ${p}: ${(err as Error).message}`)
    }
  }
  return out
}

export interface Interface {
  readonly list: () => Effect.Effect<Info[]>
  readonly get: (name: string) => Effect.Effect<Info | undefined>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Skill") {}

export interface LayerOptions {
  /** Directories to scan. Default: `$CWD/skills`, `$CWD/gateway/skills`. */
  directories?: string[]
}

export function layer(options: LayerOptions = {}): Layer.Layer<Service, Error> {
  return Layer.effect(
    Service,
    Effect.gen(function* () {
      const dirs = options.directories ?? [
        resolve(process.cwd(), "skills"),
        resolve(process.cwd(), "gateway", "skills"),
      ]

      const skills: Info[] = yield* Effect.try({
        try: () => {
          const all: Info[] = []
          for (const d of dirs) {
            if (!existsSync(d)) continue
            const s = statSync(d)
            if (!s.isDirectory()) continue
            all.push(...loadSkillsDir(d))
          }
          return all
        },
        catch: (e) => (e instanceof Error ? e : new Error(String(e))),
      })

      const byName = new Map(skills.map((s) => [s.name, s]))

      return Service.of({
        list: () => Effect.succeed(skills.slice()),
        get: (name) => Effect.succeed(byName.get(name)),
      })
    }),
  )
}

/** Default layer using default scan directories. */
export const defaultLayer = layer()
