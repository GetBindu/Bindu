import type { ZodType } from "zod"

/**
 * Typed bus event definition.
 *
 * Patterned after OpenCode's bus-event registry but without multi-instance
 * coupling. The gateway is single-instance, so we can drop the InstanceState
 * envelope and keep the registry flat.
 */
export type Definition<Type extends string = string, Props extends ZodType = ZodType> = {
  readonly type: Type
  readonly properties: Props
}

const registry = new Map<string, Definition>()

export function define<Type extends string, Properties extends ZodType>(
  type: Type,
  properties: Properties,
): Definition<Type, Properties> {
  const def: Definition<Type, Properties> = { type, properties }
  registry.set(type, def as unknown as Definition)
  return def
}

/** List all registered event definitions (used for docs / SSE projector schema). */
export function all(): Definition[] {
  return Array.from(registry.values())
}

export * as BusEvent from "./bus-event"
