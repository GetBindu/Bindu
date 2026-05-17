import { Effect, Stream } from "effect"
import { Service as BusService } from "./bus"

/**
 * Forward bus events to the inbox so it can render
 * gateway-originated A2A traffic alongside per-agent webhooks.
 *
 * Wire it in by calling `runtime.runFork(forwarderEffect)` after the
 * runtime is built. Disabled when `BINDU_COMMS_URL` is unset, so it's
 * a no-op outside the dev surface.
 *
 * The `session.prompt.started` event id is set to the messageID so
 * downstream tool / finished events can carry `parent_id = messageID`
 * — the comms inbox uses that to nest the trace under one plan row.
 *
 * `session.prompt.text` is skipped (per-token deltas would flood the
 * feed without adding value).
 */
export const forwarderEffect = Effect.gen(function* () {
  const url = process.env.BINDU_COMMS_URL
  if (!url) {
    console.log("[bindu-gateway] comms forwarder disabled (BINDU_COMMS_URL unset)")
    return
  }
  const bus = yield* BusService
  console.log(`[bindu-gateway] comms forwarder → ${url}`)

  yield* Stream.runForEach(bus.subscribeAll(), (event) => {
    if (event.type === "session.prompt.text") return Effect.void
    const props = event.properties as Record<string, unknown>
    const messageID = String(props.messageID ?? "")
    const isStart = event.type === "session.prompt.started"
    const eventId = isStart && messageID ? messageID : crypto.randomUUID()
    return Effect.tryPromise(() =>
      fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          event_id: eventId,
          timestamp: new Date().toISOString(),
          kind: "gateway-event",
          event_type: event.type,
          parent_id: isStart ? undefined : messageID || undefined,
          properties: props,
        }),
      }),
    ).pipe(Effect.catch(() => Effect.void))
  })
})
