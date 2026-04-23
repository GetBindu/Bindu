import { Context, Effect, Layer, PubSub, Stream } from "effect"
import type { z } from "zod"
import { BusEvent } from "./bus-event"

/**
 * Typed event bus for the gateway.
 *
 * Patterned after OpenCode's bus/index.ts but without Instance/Workspace
 * coupling. Single process, single bus instance.
 */

type Payload<D extends BusEvent.Definition = BusEvent.Definition> = {
  type: D["type"]
  properties: z.output<D["properties"]>
}

interface InternalState {
  readonly wildcard: PubSub.PubSub<Payload>
  readonly typed: Map<string, PubSub.PubSub<Payload>>
}

export interface Interface {
  readonly publish: <D extends BusEvent.Definition>(
    def: D,
    properties: z.output<D["properties"]>,
  ) => Effect.Effect<void>

  readonly subscribe: <D extends BusEvent.Definition>(def: D) => Stream.Stream<Payload<D>>

  readonly subscribeAll: () => Stream.Stream<Payload>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Bus") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const wildcard = yield* PubSub.unbounded<Payload>()
    const typed = new Map<string, PubSub.PubSub<Payload>>()

    yield* Effect.addFinalizer(() =>
      Effect.gen(function* () {
        yield* PubSub.shutdown(wildcard)
        for (const ps of typed.values()) yield* PubSub.shutdown(ps)
      }),
    )

    const state: InternalState = { wildcard, typed }

    function getOrCreate<D extends BusEvent.Definition>(def: D) {
      return Effect.gen(function* () {
        let ps = state.typed.get(def.type)
        if (!ps) {
          ps = yield* PubSub.unbounded<Payload>()
          state.typed.set(def.type, ps)
        }
        return ps as unknown as PubSub.PubSub<Payload<D>>
      })
    }

    const publish: Interface["publish"] = (def, properties) =>
      Effect.gen(function* () {
        const payload: Payload = { type: def.type, properties }
        const ps = state.typed.get(def.type)
        if (ps) yield* PubSub.publish(ps, payload)
        yield* PubSub.publish(state.wildcard, payload)
      })

    const subscribe: Interface["subscribe"] = (def) =>
      Stream.unwrap(
        Effect.gen(function* () {
          const ps = yield* getOrCreate(def)
          return Stream.fromPubSub(ps)
        }),
      )

    const subscribeAll: Interface["subscribeAll"] = () =>
      Stream.fromPubSub(state.wildcard)

    return Service.of({ publish, subscribe, subscribeAll })
  }),
)

export * from "./bus-event"
