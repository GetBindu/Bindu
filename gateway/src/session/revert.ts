import { Context, Effect, Layer } from "effect"
import { Service as DBService } from "../db"
import type { SessionID, MessageID } from "./schema"

/**
 * Session revert — conversation-turn rollback.
 *
 * Semantics (different from OpenCode's file-snapshot revert):
 *   - A "turn" is a user message + all assistant messages + tasks that
 *     came after it, up to the next user message.
 *   - `revertTo(messageID)` marks every message and task after the target
 *     as `reverted=true`; subsequent history() calls skip them.
 *   - `revertLastTurn()` convenience: revert everything after the next-to-
 *     latest user message. Handy for "oops, ignore my last question".
 *
 * What we do NOT do:
 *   - Send `tasks/cancel` to peers for reverted tasks. Remote agents have
 *     already done the work; the cost and side effects on their side are
 *     not reversible by our gateway. Phase 5 payment revert would need
 *     x402-specific refund handling.
 *
 * Reverted rows are retained (not deleted) so that:
 *   - Audit remains intact (operator can see the revert in the tasks table)
 *   - Undo-revert is possible (Phase 2 could expose it)
 */

export interface Interface {
  /** Mark everything strictly after `messageID` as reverted. */
  readonly revertTo: (input: {
    sessionID: SessionID
    messageID: MessageID
  }) => Effect.Effect<{ messagesReverted: number; tasksReverted: number }, Error>

  /** Revert the most recent completed turn. */
  readonly revertLastTurn: (
    sessionID: SessionID,
  ) => Effect.Effect<{ messagesReverted: number; tasksReverted: number }, Error>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/SessionRevert") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const db = yield* DBService

    const revertTo: Interface["revertTo"] = ({ sessionID, messageID }) =>
      Effect.gen(function* () {
        const client = db.client()

        // Find the target message's created_at
        const { data: target, error: tErr } = yield* Effect.promise(() =>
          client
            .from("gateway_messages")
            .select("created_at")
            .eq("id", messageID as unknown as string)
            .eq("session_id", sessionID)
            .maybeSingle(),
        )
        if (tErr) return yield* Effect.fail(new Error(`revertTo: ${tErr.message}`))
        if (!target) {
          return yield* Effect.fail(new Error(`revertTo: message ${messageID} not found in session`))
        }

        const boundary = (target as { created_at: string }).created_at

        const { data: mUpdated, error: mErr } = yield* Effect.promise(() =>
          client
            .from("gateway_messages")
            .update({ reverted: true })
            .eq("session_id", sessionID)
            .gt("created_at", boundary)
            .select("id"),
        )
        if (mErr) return yield* Effect.fail(new Error(`revertTo messages: ${mErr.message}`))

        const { data: tUpdated, error: tRevErr } = yield* Effect.promise(() =>
          client
            .from("gateway_tasks")
            .update({ reverted: true })
            .eq("session_id", sessionID)
            .gt("started_at", boundary)
            .select("id"),
        )
        if (tRevErr) return yield* Effect.fail(new Error(`revertTo tasks: ${tRevErr.message}`))

        return {
          messagesReverted: mUpdated?.length ?? 0,
          tasksReverted: tUpdated?.length ?? 0,
        }
      })

    const revertLastTurn: Interface["revertLastTurn"] = (sessionID) =>
      Effect.gen(function* () {
        const client = db.client()

        // Find the 2nd most recent user message — revert to THAT.
        // (revert means "drop everything after", so to drop the latest
        // turn we point at the penultimate user message.)
        const { data: userMsgs, error } = yield* Effect.promise(() =>
          client
            .from("gateway_messages")
            .select("id, created_at")
            .eq("session_id", sessionID)
            .eq("role", "user")
            .eq("reverted", false)
            .order("created_at", { ascending: false })
            .limit(2),
        )
        if (error) return yield* Effect.fail(new Error(`revertLastTurn: ${error.message}`))
        if (!userMsgs || userMsgs.length < 2) {
          return { messagesReverted: 0, tasksReverted: 0 }
        }
        const penultimate = userMsgs[1] as { id: string; created_at: string }
        return yield* revertTo({
          sessionID,
          messageID: penultimate.id as unknown as MessageID,
        })
      })

    return Service.of({ revertTo, revertLastTurn })
  }),
)
