import type { ZodType } from "zod"

/**
 * Minimal YAML frontmatter parser for gateway markdown configs.
 *
 * Used by the agent loader and the recipe loader. Kept intentionally small —
 * if authors need richer YAML, pull in `js-yaml` explicitly.
 *
 * Scope: YAML features the gateway's frontmatter blocks actually use.
 *
 *   - `key: value`
 *   - nested maps (indentation-based)
 *   - inline arrays: `tags: [a, b, "c"]`
 *   - scalars: string (bare or quoted), number, boolean, null
 */

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
export function parseYaml(src: string): Record<string, unknown> {
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

/** Split frontmatter and parse the YAML block in one call. */
export function parseFrontmatterDoc(raw: string): {
  fm: Record<string, unknown>
  body: string
} {
  const { frontmatter, body } = splitFrontmatter(raw)
  return { fm: frontmatter ? parseYaml(frontmatter) : {}, body }
}

/**
 * Parse a markdown doc's frontmatter, build a candidate via `build`, and
 * validate against `schema`. Consolidates the loader pattern shared by agent
 * and recipe: both split→parseYaml→buildCandidate→safeParse→throwOnError.
 */
export function parseMarkdownWithSchema<T>(args: {
  path: string
  raw: string
  kind: string
  schema: ZodType<T>
  build: (fm: Record<string, unknown>, body: string) => unknown
}): T {
  const { fm, body } = parseFrontmatterDoc(args.raw)
  const candidate = args.build(fm, body)
  const result = args.schema.safeParse(candidate)
  if (!result.success) {
    throw new Error(
      `${args.kind}: invalid frontmatter in ${args.path}: ${result.error.message}`,
    )
  }
  return result.data
}

export function parseScalar(s: string): unknown {
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
