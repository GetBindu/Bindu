import { Context, Effect, Layer } from "effect"
import { z } from "zod"

/**
 * Permission ruleset for the gateway.
 *
 * Minimal, pattern-matching wildcard evaluator.
 *
 * Rules are keyed by permission key (`agent_call`, `tasks/cancel`, etc.) and
 * map wildcard patterns to one of `allow | deny | ask`. Most-specific match
 * wins. Unknown permission keys resolve to the configured default (default
 * `ask`).
 *
 * Phase 3 adds inbound `bindu_expose` rules; the evaluator generalizes.
 */

export const Action = z.enum(["allow", "deny", "ask"])
export type Action = z.infer<typeof Action>

export const Rule = z.object({
  permission: z.string(),
  pattern: z.string().default("*"),
  action: Action,
})
export type Rule = z.infer<typeof Rule>

export const Ruleset = z.array(Rule)
export type Ruleset = z.infer<typeof Ruleset>

/**
 * Parse a config-file permission block into a flat Ruleset.
 *
 * Accepted shapes:
 *   { "bash": "allow" }
 *   { "edit": { "*.md": "allow", "*.key": "deny" } }
 *   { "agent_call": { "research": "allow", "*": "deny" } }
 */
export function fromConfig(
  raw: Record<string, unknown> | undefined,
): Ruleset {
  if (!raw) return []
  const rules: Rule[] = []
  for (const [permission, value] of Object.entries(raw)) {
    if (typeof value === "string") {
      const action = Action.parse(value)
      rules.push({ permission, pattern: "*", action })
      continue
    }
    if (value && typeof value === "object") {
      for (const [pattern, action] of Object.entries(value as Record<string, unknown>)) {
        rules.push({
          permission,
          pattern,
          action: Action.parse(action),
        })
      }
    }
  }
  return rules
}

/** Merge multiple rulesets; later entries win for the same (permission, pattern). */
export function merge(...sets: (Ruleset | undefined | null)[]): Ruleset {
  const map = new Map<string, Rule>()
  for (const set of sets) {
    if (!set) continue
    for (const rule of set) {
      map.set(`${rule.permission}\0${rule.pattern}`, rule)
    }
  }
  return Array.from(map.values())
}

/** Wildcard match: `*` matches any, `**` matches any including dots. */
function globToRegex(glob: string): RegExp {
  const s = glob
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*\*/g, "::GLOBSTAR::")
    .replace(/\*/g, "[^/:]*")
    .replace(/::GLOBSTAR::/g, ".*")
    .replace(/\?/g, ".")
  return new RegExp(`^${s}$`)
}

function specificity(pattern: string): number {
  // More concrete (fewer wildcards, longer literal) = higher specificity.
  let score = pattern.length
  if (pattern === "*") score = -100
  if (pattern.includes("**")) score -= 10
  if (pattern.includes("*")) score -= 1
  return score
}

export interface EvaluateInput {
  permission: string
  target?: string       // pattern-matched against rules; e.g. peer name or skill id
  defaultAction?: Action
}

export function evaluate(ruleset: Ruleset, input: EvaluateInput): Action {
  const target = input.target ?? "*"
  const candidates = ruleset
    .filter((r) => r.permission === input.permission)
    .filter((r) => globToRegex(r.pattern).test(target))
    .sort((a, b) => specificity(b.pattern) - specificity(a.pattern))

  if (candidates.length > 0) return candidates[0].action
  return input.defaultAction ?? "ask"
}

export interface Interface {
  readonly evaluate: (rulesets: (Ruleset | undefined)[], input: EvaluateInput) => Effect.Effect<Action>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Permission") {}

export const layer = Layer.effect(
  Service,
  Effect.succeed(
    Service.of({
      evaluate: (rulesets, input) =>
        Effect.sync(() => {
          const merged = merge(...rulesets)
          return evaluate(merged, input)
        }),
    }),
  ),
)
